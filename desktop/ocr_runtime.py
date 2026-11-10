"""Keep short-lived OCR workers quiet and below the game's scheduling priority."""
import os
import subprocess
import time
from enum import Enum, auto


def run_ocr(command, **options):
    environment = dict(os.environ, **options.pop('env', {}))
    environment.update(OMP_THREAD_LIMIT='1', OMP_NUM_THREADS='1')
    flags = options.pop('creationflags', 0)
    if os.name == 'nt':
        flags |= getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        flags |= getattr(subprocess, 'BELOW_NORMAL_PRIORITY_CLASS', 0)
    return subprocess.run(command, env=environment, creationflags=flags, **options)

class ReadPhase(Enum):
    PENDING = auto()
    EXPIRED = auto()
    DELIVERED = auto()


class ReaderAttempt:
    """A deadline for UI ownership. An expired worker cannot publish a result."""

    def __init__(self, seconds, craft_epoch=None):
        self.deadline = time.monotonic() + seconds
        self.phase = ReadPhase.PENDING
        self.worker_done = False
        self.craft_epoch = craft_epoch

    def run(self, work):
        try:
            work()
        finally:
            self.worker_done = True

    def can_publish(self):
        return self.phase is ReadPhase.PENDING and time.monotonic() < self.deadline

    @property
    def expired(self):
        return self.phase is ReadPhase.EXPIRED

    def claim(self):
        if not self.can_publish():
            return False
        self.phase = ReadPhase.DELIVERED
        return True

    def expire(self):
        if self.phase is not ReadPhase.PENDING or time.monotonic() < self.deadline:
            return False
        self.phase = ReadPhase.EXPIRED
        return True
