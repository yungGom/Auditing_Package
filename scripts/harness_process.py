"""Bounded Harness subprocesses; no persisted raw output or secrets."""
from pathlib import Path
import os
import signal
import sys
import subprocess
import tempfile
import time


def run_check(argv, cwd, timeout):
    if timeout <= 0:
        raise ValueError('timeout must be positive')
    started = time.monotonic()
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    with tempfile.TemporaryFile() as output:
        options = {'start_new_session': True} if os.name != 'nt' else {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP}
        try:
            process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, **options)
        except OSError as exc:
            return {'status': 'NOT RUN', 'reason': 'EXECUTION_UNAVAILABLE', 'error_class': type(exc).__name__, 'exit_code': None, 'duration_seconds': 0}
        try:
            code = process.wait(timeout=timeout)
            result = {'status': 'PASS' if code == 0 else 'FAIL', 'reason': 'COMPLETED', 'exit_code': code}
        except subprocess.TimeoutExpired:
            # Kill descendants while their root PID still exists. Never leave a build/test running after timeout.
            if os.name == 'nt':
                killer = Path(os.environ['SystemRoot']) / 'System32' / 'taskkill.exe'
                try:
                    subprocess.run([str(killer), '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=False)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            else:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if process.poll() is None:
                process.kill()
            process.wait(timeout=15)
            result = {'status': 'FAIL', 'reason': 'TIMEOUT', 'exit_code': process.returncode}
        result['duration_seconds'] = round(time.monotonic() - started, 2)
        # Only console feedback; never place raw test output in JSON evidence.
        output.seek(0)
        text = output.read().decode('utf-8', errors='replace')
        encoding = sys.stdout.encoding or 'utf-8'
        print(text.encode(encoding, errors='backslashreplace').decode(encoding), end='', flush=True)
        return result
