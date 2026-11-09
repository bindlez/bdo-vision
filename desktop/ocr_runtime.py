"""Keep short-lived OCR workers quiet and below the game's scheduling priority."""
import os
import subprocess
import time


def run_ocr(command, **options):
    environment = dict(os.environ, **options.pop('env', {}))
    environment.update(OMP_THREAD_LIMIT='1', OMP_NUM_THREADS='1')
    flags = options.pop('creationflags', 0)
    if os.name == 'nt':
        flags |= getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        flags |= getattr(subprocess, 'BELOW_NORMAL_PRIORITY_CLASS', 0)
    return subprocess.run(command, env=environment, creationflags=flags, **options)

class ReaderAttempt:
    """A deadline for UI ownership. An expired worker cannot publish a result."""

    def __init__(self, seconds):
        self.deadline = time.monotonic() + seconds
        self.expired = False
        self.worker_done = False

    def run(self, work):
        try:
            work()
        finally:
            self.worker_done = True

    def can_publish(self):
        return not self.expired and time.monotonic() < self.deadline

    def expire(self):
        if self.expired or time.monotonic() < self.deadline:
            return False
        self.expired = True
        return True
