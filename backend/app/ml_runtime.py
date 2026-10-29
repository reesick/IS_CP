"""One reusable ML child, isolated from API imports and serialized by the worker."""
import subprocess
import time
import os
from .settings import ROOT, DATA, ML_PYTHON, settings


class MLRuntime:
    def __init__(self):
        self.process = None
        self.log = None
        self.last_used = 0

    def submit(self, request_path):
        if self.process is None or self.process.poll() is not None:
            self.close()
            log_path = DATA / 'logs' / 'ml-runtime.log'
            log_path.parent.mkdir(parents=True, exist_ok=True)
            self.log = log_path.open('a', encoding='utf-8')
            self.process = subprocess.Popen(
                [str(ML_PYTHON), '-u', '-m', 'backend.app.ml_runner', '--serve'],
                cwd=ROOT, stdin=subprocess.PIPE, stdout=self.log, stderr=self.log,
                text=True, encoding='utf-8',
                env=dict(os.environ,IMAGESHIELD_WORKER_PID=str(os.getpid())),
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
        self.process.stdin.write(str(request_path) + '\n')
        self.process.stdin.flush()
        self.last_used = time.monotonic()
        return self.process

    def mark_idle(self):
        self.last_used = time.monotonic()

    def trim_idle(self):
        if self.process is not None and time.monotonic() - self.last_used > settings.model_idle_seconds:
            self.close()

    def close(self):
        process, self.process = self.process, None
        if process is not None:
            if process.poll() is None:
                if process.stdin:
                    process.stdin.close()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    if os.name=='nt':
                        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    else:
                        process.kill()
                    process.wait(timeout=15)
            elif process.stdin:
                process.stdin.close()
        if self.log:
            self.log.close()
            self.log = None
