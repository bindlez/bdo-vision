"""Optional persistent OS OCR transport. No screenshots on disk or game input.

An unavailable Windows English language pack is an explicit unavailable state,
never an installation request or a fabricated read. Production enables this
backend only after its replay and installed-app gates pass.
"""
import io
import json
import queue
import struct
import subprocess
import threading
from pathlib import Path


class WindowsOCR:
    def __init__(self,executable):
        self.executable=Path(executable);self.process=None;self.messages=None
        self.lock=threading.Lock();self.info=None

    def _receive(self,timeout):
        try:line=self.messages.get(timeout=timeout)
        except queue.Empty:raise RuntimeError('Windows OCR reached its deadline') from None
        if line is None:raise RuntimeError('Windows OCR worker stopped')
        if len(line)>1_000_000:raise RuntimeError('Windows OCR response exceeds its budget')
        data=json.loads(line)
        if not isinstance(data,dict):raise RuntimeError('Invalid Windows OCR response')
        if data.get('error'):raise RuntimeError(str(data['error'])[:200])
        return data

    def _start(self):
        if self.process is not None and self.process.poll() is None:return
        if not self.executable.is_file():raise RuntimeError('Windows OCR helper is not installed')
        self.messages=queue.Queue(maxsize=2)
        self.process=subprocess.Popen([str(self.executable)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'BELOW_NORMAL_PRIORITY_CLASS',0))
        output=self.process.stdout;messages=self.messages
        def receive():
            try:
                while True:
                    line=output.readline(1_000_001)
                    if not line:break
                    if line.strip():
                        try:messages.put_nowait(line)
                        except queue.Full:break
            finally:
                try:messages.put_nowait(None)
                except queue.Full:pass
        threading.Thread(target=receive,name='vision-os-ocr-pipe',daemon=True).start()
        self.info=self._receive(5)
        if self.info.get('ready') is not True:raise RuntimeError('Windows OCR unavailable')

    def recognize(self,image,timeout=2):
        if min(image.size)<1 or image.width*image.height>1_500_000:raise ValueError('OCR crop exceeds its pixel budget')
        with self.lock:
            try:
                self._start();buffer=io.BytesIO();image.convert('RGB').save(buffer,format='PNG');blob=buffer.getvalue()
                if len(blob)>2_000_000:raise ValueError('OCR crop exceeds its transport budget')
                self.process.stdin.write(struct.pack('<I',len(blob))+blob);self.process.stdin.flush()
                result=self._receive(timeout);words=result.get('words',[])
                if not isinstance(words,list) or len(words)>6000:raise RuntimeError('Invalid positioned words')
                # Keep engine-provided row boundaries instead of flattening wrapped
                # progress text and accidentally mixing neighboring objectives.
                lines={}
                for word in words:
                    lines.setdefault(word['line'],[]).append(str(word['text']))
                result['text']='\n'.join(' '.join(line) for line in lines.values())
                return result
            except Exception:
                self.close();raise

    def close(self):
        process=self.process;self.process=None;self.info=None
        if process is not None:
            if process.poll() is None:process.kill()
            try:process.communicate(timeout=2)
            except (subprocess.TimeoutExpired,ValueError):pass
