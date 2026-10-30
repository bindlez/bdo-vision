"""Measured capture coverage. Unobserved gaps never become earned loot."""
import time
import uuid


class CaptureClock:
    def __init__(self,db,now=None):
        self.db=db
        db.execute('CREATE TABLE IF NOT EXISTS capture_clock (id INTEGER PRIMARY KEY CHECK(id=1), history_id TEXT NOT NULL, observed REAL NOT NULL, paused REAL NOT NULL)')
        db.execute('INSERT OR IGNORE INTO capture_clock VALUES (1,?,0,0)',(uuid.uuid4().hex,));db.commit()
        db.execute('CREATE TABLE IF NOT EXISTS capture_spans (id INTEGER PRIMARY KEY, started_at REAL NOT NULL, ended_at REAL NOT NULL)')
        db.execute('CREATE INDEX IF NOT EXISTS capture_spans_time ON capture_spans(ended_at,started_at)');db.commit()
        self.history_id,self.observed,self.paused=db.execute('SELECT history_id,observed,paused FROM capture_clock WHERE id=1').fetchone()
        self.last=time.monotonic() if now is None else now
        self.available=False;self.reason='Waiting for a readable capture';self.last_saved=self.last
        self.span_id=None;self.span_end=None

    def tick(self,available,reason='',now=None,wall=None):
        now=time.monotonic() if now is None else now;elapsed=max(0,now-self.last)
        wall=time.time() if wall is None else wall
        # Long UI/OS suspensions are missing observation, not active tracking.
        if self.available and available and elapsed<=5:
            self.observed+=elapsed
            if elapsed>0:
                start=wall-elapsed
                with self.db:
                    if self.span_id and self.span_end is not None and abs(start-self.span_end)<.05:
                        self.db.execute('UPDATE capture_spans SET ended_at=? WHERE id=?',(wall,self.span_id))
                    else:self.span_id=self.db.execute('INSERT INTO capture_spans(started_at,ended_at) VALUES (?,?)',(start,wall)).lastrowid
                self.span_end=wall
        else:self.paused+=elapsed;self.span_id=None;self.span_end=None
        self.last=now;self.available=bool(available);self.reason='' if available else reason
        if now-self.last_saved>=2:self.save()
        return self.snapshot()

    def snapshot(self):
        return {'history_id':self.history_id,'observed_seconds':round(self.observed,3),'paused_seconds':round(self.paused,3),'available':self.available,'reason':self.reason}

    def save(self):
        with self.db:self.db.execute('UPDATE capture_clock SET observed=?,paused=? WHERE id=1',(self.observed,self.paused))
        self.last_saved=self.last
