"""Pure scanning policies: fast-pass schedule, confidence and sync throttling."""
from collections import Counter


def select_ocr_passes():
    """Ordered cheap recognition passes, with more expensive fallbacks."""
    return (('contrast', 7), ('inverted', 7), ('contrast', 6),
            ('threshold', 7), ('natural', 13), ('inverted', 6))


def candidate_is_stable(candidates, expected=None, expected_max=None):
    """Require agreement from two passes before stopping early."""
    votes = Counter((int(a), int(b)) for a,b in candidates if b > 0 and 0 <= a <= b)
    if not votes:
        return False
    (value, maximum), count = votes.most_common(1)[0]
    if count < 2:
        return False
    if expected_max is not None and maximum != expected_max:
        return False
    if expected is not None and abs(value-expected) > max(45, maximum*.045):
        return False
    return True


def should_publish(last, current, last_at, now, session_id, min_change=2, heartbeat=60):
    """Publish immediately for real changes, changed tool sessions or heartbeat."""
    if last is None:
        return True
    old_value, old_max, old_session = last
    value, maximum = current
    if old_session != session_id or old_max != maximum:
        return True
    return abs(value-old_value) >= min_change or now-last_at >= heartbeat


class SpeedEstimator:
    """Passive pace estimator: never silently changes the user's craft timing."""
    def __init__(self):
        self.last = None
        self.samples = []

    def reset(self):
        self.last = None
        self.samples.clear()

    def add(self, current, maximum, timestamp, session_id):
        reading = (int(current), int(maximum), float(timestamp), str(session_id))
        if self.last is not None:
            prev, prev_max, when, session = self.last
            delta = prev - reading[0]
            elapsed = reading[2] - when
            if session != reading[3] or prev_max != reading[1] or delta < 0:
                self.reset()
            elif delta >= 2 and elapsed >= 1:
                rate = elapsed / delta
                if 0.10 <= rate <= 120:
                    self.samples.append(rate)
                    self.samples = self.samples[-7:]
            elif delta == 0:
                # Update timestamp only when durability changes; a stationary
                # tool is not a reason to infer an absurd craft speed.
                return self.estimate()
        self.last = reading
        return self.estimate()

    def estimate(self):
        if len(self.samples) < 2:
            return None
        ordered = sorted(self.samples)
        return ordered[len(ordered)//2]
