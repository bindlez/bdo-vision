"""Compare native glyph and production OCR readers on labeled text-feed frames.

Each frame runs in a fresh process. Reports contain timings, sampled peak
private memory and row comparisons. They do not measure unique drop accuracy.
"""
import argparse
from collections import Counter
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]


def ocr_worker(image_path, catalog_path, tesseract, helper):
    sys.path.insert(0, str(ROOT / 'desktop'))
    from PIL import Image
    from item_catalog import DiskItemDatabase
    from loot_capture import recognize_feed
    from price_book import PriceBook
    from windows_ocr import WindowsOCR

    book = PriceBook(':memory:')
    book._item_database = DiskItemDatabase(catalog_path)
    worker = WindowsOCR(helper) if helper else None
    try:
        with Image.open(image_path) as image:
            started = time.perf_counter()
            result = recognize_feed(image, tesseract, 'chat', False, ROOT / 'build',
                                    resolve_name=book.resolve_name, diagnostics=False,
                                    positioned_worker=worker)
            elapsed = (time.perf_counter() - started) * 1000
        print(json.dumps({'rows': [[event.item, event.quantity] for event in result['events']],
                          'reader_ms': elapsed}))
    finally:
        if worker:
            worker.close()


def run_measured(command):
    import psutil

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, *([ctypes.POINTER(wintypes.FILETIME)] * 4)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    started = time.perf_counter()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, cwd=ROOT)
    root = psutil.Process(process.pid)
    peak_private = 0
    handles = {}
    while process.poll() is None:
        total = 0
        try:
            children = root.children(recursive=True)
            for child in [root, *children]:
                try:
                    if child.pid not in handles:
                        handle = kernel.OpenProcess(0x1000, False, child.pid)
                        if handle:
                            handles[child.pid] = handle
                    total += child.memory_full_info().private
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        peak_private = max(peak_private, total)
        time.sleep(.01)
    stdout, stderr = process.communicate(timeout=10)
    cpu_ticks = 0
    for handle in handles.values():
        created, exited, kernel_time, user_time = (wintypes.FILETIME() for _ in range(4))
        if kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited),
                                  ctypes.byref(kernel_time), ctypes.byref(user_time)):
            cpu_ticks += ((kernel_time.dwHighDateTime << 32) | kernel_time.dwLowDateTime)
            cpu_ticks += ((user_time.dwHighDateTime << 32) | user_time.dwLowDateTime)
        kernel.CloseHandle(handle)
    if process.returncode:
        raise RuntimeError(f'Benchmark worker failed: {stderr[:400]}')
    return json.loads(stdout), (time.perf_counter() - started) * 1000, peak_private, cpu_ticks / 10000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--image', type=Path)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--tesseract', required=True)
    parser.add_argument('--helper', type=Path)
    parser.add_argument('--native', type=Path)
    parser.add_argument('--labels', type=Path)
    parser.add_argument('--frames', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.worker:
        ocr_worker(args.image, args.catalog, args.tesseract, args.helper)
        return
    if not all((args.native, args.labels, args.frames, args.output)):
        parser.error('Comparison needs native, labels, frames and output paths')
    labels = json.loads(args.labels.read_text(encoding='utf-8-sig'))
    results = []
    for filename, expected in labels.items():
        image = (args.frames / filename).resolve()
        native_cmd = [str(args.native.resolve()), '--image', str(image), '--ensemble']
        ocr_cmd = [sys.executable, str(Path(__file__).resolve()), '--worker', '--image', str(image),
                   '--catalog', str(args.catalog.resolve()), '--tesseract', args.tesseract]
        if args.helper:
            ocr_cmd.extend(['--helper', str(args.helper.resolve())])
        for mode, command in [('glyph', native_cmd), ('ocr', ocr_cmd)]:
            report, wall_ms, peak, cpu_ms = run_measured(command)
            rows = report['rows']
            actual = Counter((row['item'], row['quantity']) for row in rows if row['item']) if mode == 'glyph' else Counter(map(tuple, rows))
            truth = Counter(map(tuple, expected))
            results.append({'frame': filename, 'reader': mode,
                            'matched': sum((truth & actual).values()),
                            'missed': sum((truth - actual).values()),
                            'extra': sum((actual - truth).values()),
                            'reader_ms': report.get('cold_ms', report.get('reader_ms')),
                            'wall_ms': round(wall_ms, 2), 'sampled_peak_private_bytes': peak,
                            'observed_process_tree_cpu_ms': round(cpu_ms, 2),
                            'actual': list(actual.elements()), 'expected': expected})
            print(f'{filename} {mode}: {results[-1]["matched"]} matched, '
                  f'{results[-1]["missed"]} missed, {results[-1]["extra"]} extra', flush=True)
    args.output.write_text(json.dumps({'results': results}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
