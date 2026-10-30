"""Pure, testable OCR consensus and bracket/one correction.

Never change a reading based on its leading 1 alone: the prior timer must
strongly support the shorter candidate and reject the raw candidate.
"""
from collections import Counter
import re


def choose_reading(readings, expected=None, expected_max=None):
    """Return (current, maximum), votes, corrected_flag for OCR passes."""
    votes = Counter((int(a), int(b)) for a, b in readings
                    if int(b) > 0 and 0 <= int(a) <= int(b))
    if not votes:
        raise ValueError('No valid OCR durability readings')
    def score(item):
        (current, maximum), count = item
        value = count * 3
        if expected_max is not None and maximum == expected_max:
            value += 2
        if expected is not None and maximum == expected_max:
            distance = abs(current-expected)
            value += 6 if distance <= max(18, expected*.045) else 0
        return value
    raw, n = max(votes.items(), key=score)
    current, maximum = raw
    corrected = False
    if (expected is not None and maximum == expected_max
            and 1000 <= current <= 1999 and str(current).startswith('1')):
        shorter = int(str(current)[1:])
        tolerance = max(20, expected*.055)
        if (abs(shorter-expected) <= tolerance
                and abs(current-expected) > max(120,maximum*.1)):
            current = shorter
            corrected = True
    return (current, maximum), n, corrected


def reading_is_plausible(current, maximum, estimate, previous_maximum):
    """Reject implausible jumps until a confirming scan arrives."""
    if maximum != previous_maximum:
        return False
    return abs(current-estimate) <= max(30, maximum*.03)


# Accept optional parentheses and grouped thousands separators without silently
# truncating a legitimate number like 1,350 to 350.
_PAIR_TEXT = re.compile(r"(?<![\d,])\(?\s*([1-9]\d{0,5}|0|[1-9]\d{0,2}(?:,\d{3}){1,2})\s*[)/|]\s*([1-9]\d{0,5}|[1-9]\d{0,2}(?:,\d{3}){1,2})\s*\)?(?![\d,])")


def extract_pairs(text):
    """Return plausible (current, maximum) durability pairs from OCR text.

    Broken labels, e.g. a clipped "35/", are never treated as a reading.
    The `1` vs `(` ambiguity remains subject to OCR consensus in choose_reading.
    """
    out = []
    for match in _PAIR_TEXT.finditer(str(text)):
        current = int(match.group(1).replace(',', ''))
        maximum = int(match.group(2).replace(',', ''))
        if 0 <= current <= maximum and maximum > 0:
            out.append((current, maximum))
    return out
