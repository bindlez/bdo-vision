"""Pure durability signal validation, independent of Tk, Windows and OCR.

An OCR digit is not a new tool until confirmed, and a delayed capture is not a
reading from the time the OCR subprocess finishes. No guessing while uncertain.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    kind: str  # accept, confirm, new_tool
    message: str = ''


class ReadingGate:
    def __init__(self):
        self.pending = None
        self.pending_at = 0.0

    def evaluate(self, reading, expected, maximum, at, votes=1, has_baseline=False):
        current, cap = map(int, reading)
        if current < 0 or cap <= 0 or current > cap:
            return Decision('confirm', 'Invalid durability; ignored')
        initial = not has_baseline
        outlier = (not initial and
                   (cap != maximum or abs(current - expected) > max(30, cap * .03)))
        # Require initial corroboration and separate confirmations of major changes.
        if not initial and not outlier:
            self.pending = None
            return Decision('accept')
        if initial and votes >= 2:
            self.pending = None
            return Decision('accept')
        candidate = self.pending
        corroborated = (candidate is not None and
                        candidate[1] == cap and
                        abs(candidate[0] - current) <= max(15, cap * .015) and
                        0 <= at - self.pending_at <= 35)
        if corroborated:
            self.pending = None
            # A sudden LOWER durability can be a delayed scan, OCR jump, or
            # another visible utensil. Do not create a fresh tool session on a
            # downward change: only a confirmed refill or capacity change can.
            is_new_tool = (cap != maximum or (expected is not None and current > expected))
            return Decision('new_tool' if outlier and is_new_tool else 'accept')
        self.pending = (current, cap)
        self.pending_at = at
        if initial:
            return Decision('confirm', 'Checking first OCR reading…')
        return Decision('confirm', 'Unexpected reading; verifying before changing timer…')


def remaining_at(value, anchor_mono, when_mono, seconds_per_craft, running):
    if not running or anchor_mono is None:
        return max(0., float(value))
    return max(0., float(value) - max(0., when_mono - anchor_mono) / max(.05, float(seconds_per_craft)))


def align_to_capture(current, captured_mono, processed_mono, seconds_per_craft):
    """Compensate OCR processing time without subtracting double-counted seconds."""
    return remaining_at(current, captured_mono, processed_mono, seconds_per_craft, True)


def estimate_send(value, anchor_mono, now, seconds_per_craft, running):
    """Round up durability: avoids losing a craft due to timer fractional parts."""
    import math
    return int(math.ceil(remaining_at(value, anchor_mono, now, seconds_per_craft, running) - 1e-9))


def replacement_needs_use(previous_key,new_key,remaining,current,maximum,wear_streak,manual=False):
    """Near exhaustion, position alone must not reset onto a fresh neighbor."""
    return (not manual and previous_key is not None and previous_key!=new_key
            and (current<remaining or remaining<=max(10,maximum*.01))
            and abs(current-remaining)>max(30,maximum*.03) and wear_streak<2)
