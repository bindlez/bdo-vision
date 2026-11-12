"""Replay-only popup reader. Two of three reads must agree on item and quantity."""
import io
from dataclasses import replace

from PIL import ImageOps

from item_events import agreed_events, parse_events
from loot_capture import notification_ink
from loot_positioned import physical_rows
from ocr_runtime import run_ocr


def recognize_popup(image, tess, worker, resolve_name, crafting=False):
    text = image.crop((round(image.width * .16), 0, image.width, image.height))
    raw = []
    for view in (text, ImageOps.autocontrast(text.convert('L'))):
        scale = min(2, (1_500_000 / (view.width * view.height)) ** .5)
        frame = view.resize((max(1, int(view.width * scale)), max(1, int(view.height * scale))))
        words = worker.recognize(frame, timeout=2)['words']
        raw.append('\n'.join(physical_rows(words)))

    blob = io.BytesIO()
    notification_ink(text, 95, False).save(blob, format='PNG')
    result = run_ocr([tess, 'stdin', 'stdout', '--psm', '6', '-l', 'eng'],
                     input=blob.getvalue(), capture_output=True, timeout=4, check=True)
    raw.append(result.stdout.decode('utf-8', 'replace'))
    readings = []
    for output in raw:
        rows = parse_events(output, crafting=crafting, bare_items=True)
        readings.append([replace(event, item=name) for event in rows if (name := resolve_name(event.item))])
    return {'events': agreed_events(readings), 'empty': all(not output.strip() for output in raw)}
