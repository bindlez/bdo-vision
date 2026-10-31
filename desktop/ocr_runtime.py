"""Keep short-lived OCR workers quiet and below the game's scheduling priority."""
import os
import subprocess


def run_ocr(command, **options):
    environment = dict(os.environ, **options.pop('env', {}))
    environment.update(OMP_THREAD_LIMIT='1', OMP_NUM_THREADS='1')
    flags = options.pop('creationflags', 0)
    if os.name == 'nt':
        flags |= getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        flags |= getattr(subprocess, 'BELOW_NORMAL_PRIORITY_CLASS', 0)
    return subprocess.run(command, env=environment, creationflags=flags, **options)
