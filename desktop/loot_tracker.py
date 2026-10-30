"""Local loot ledger and conservative English loot-message recognition.

Snapshots overlap; identical retained rows must not become new events. The first
snapshot establishes a baseline. Ambiguous non-overlapping snapshots are skipped.
"""
import csv
import re
import sqlite3
from datetime import datetime


def parse_loot(text):
    rows = []
    pattern = re.compile(r'(?:you\s+(?:have\s+)?(?:obtained|received)|obtained)\s*:?\s*\[([^\]\n]{1,100})\]\s*(?:[x×]\s*([\d,]+)|\(([\d,]+)\))?\s*[.!]?\s*$', re.I)
    for line in text.splitlines():
        match = pattern.search(line.strip())
        if match:
            item = ' '.join(match[1].split())
            quantity = int((match[2] or match[3] or '1').replace(',', ''))
            if item and 0 < quantity <= 1_000_000:
                rows.append((item, quantity))
    return rows


class LootSnapshots:
    def __init__(self):
        self.previous = None

    def ingest(self, rows):
        """Return (new rows, ambiguous). Empty/unreadable scans keep the baseline."""
        if not rows:
            return [], False
        rows = list(rows)
        old = self.previous
        self.previous = rows
        if old is None or rows == old:
            return [], False
        for size in range(min(len(old), len(rows)), 0, -1):
            if old[-size:] == rows[:size]:
                return rows[size:], False
        # No safe scrolling overlap: skip candidates without committing totals.
        return rows, True


class LootLedger:
    def __init__(self, path):
        self.db = sqlite3.connect(str(path))
        self.db.execute('CREATE TABLE IF NOT EXISTS loot (id INTEGER PRIMARY KEY, recorded_at TEXT NOT NULL, session TEXT NOT NULL, item TEXT NOT NULL, quantity INTEGER NOT NULL, source TEXT NOT NULL)')
        if 'kind' not in {r[1] for r in self.db.execute('PRAGMA table_info(loot)')}:
            self.db.execute("ALTER TABLE loot ADD COLUMN kind TEXT NOT NULL DEFAULT 'Drop'")
        self.db.commit()

    def add(self, item, quantity, source='OCR', session='', recorded_at=None,kind='Drop'):
        item = ' '.join(str(item).split())
        quantity = int(quantity)
        if not item or len(item) > 100 or not 1 <= quantity <= 1_000_000:
            raise ValueError('Enter an item name and quantity between 1 and 1,000,000.')
        with self.db:
            cursor = self.db.execute('INSERT INTO loot(recorded_at, session, item, quantity, source, kind) VALUES (?, ?, ?, ?, ?, ?)', (recorded_at or datetime.now().astimezone().isoformat(timespec='milliseconds'), session, item, quantity, source, kind))
        return cursor.lastrowid

    def rows(self):
        return self.db.execute('SELECT id, recorded_at, item, quantity, source, session, kind FROM loot ORDER BY id DESC').fetchall()

    def mark_rare(self,row_id,kind="Rare drop"):
        with self.db:self.db.execute("UPDATE loot SET kind=? WHERE id=?",(kind,row_id))

    def export(self, path):
        with open(path, 'w', newline='', encoding='utf-8-sig') as stream:
            writer = csv.writer(stream)
            writer.writerow(['ID', 'Observed locally at', 'Item', 'Quantity', 'Source', 'Session', 'Category'])
            for row in reversed(self.rows()):
                # Keep imported names from becoming spreadsheet formulas.
                writer.writerow(["'" + value if isinstance(value, str) and value.startswith(('=', '+', '-', '@')) else value for value in row])

    def close(self):
        self.db.close()
