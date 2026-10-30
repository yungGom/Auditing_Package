"""Bounded Harness subprocesses; no persisted raw output or secrets."""
import os
import math
import signal
import sys
import subprocess
import tempfile
import time


def run_check(argv, cwd, timeout):
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('timeout must be positive')
    started = time.monotonic()
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    job = None
    process = None
    with tempfile.TemporaryFile() as output:
        options = {'start_new_session': True}
        try:
            if os.name == 'nt':
                from windows_job import WindowsJob
                job = WindowsJob()
                options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | 0x4}  # CREATE_SUSPENDED
            process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, **options)
            if job:
                job.start(process)
        except OSError as exc:
            # Child is still suspended if containment setup failed. Never run an uncontained child.
            cleanup = stop(process, job)
            return {'status': 'NOT RUN' if cleanup else 'FAIL',
                    'reason': 'EXECUTION_UNAVAILABLE' if cleanup else 'CLEANUP_FAILED',
                    'error_class': type(exc).__name__, 'exit_code': None, 'duration_seconds': 0}
        try:
            code = process.wait(timeout=timeout)
            result = {'status': 'PASS' if code == 0 else 'FAIL', 'reason': 'COMPLETED', 'exit_code': code}
        except subprocess.TimeoutExpired:
            result = {'status': 'FAIL', 'reason': 'TIMEOUT', 'exit_code': None}
        # Close the Job / process group even on normal root exit: background descendants cannot leak.
        if not stop(process, job):
            result.update(status='FAIL', reason='CLEANUP_FAILED')
        result['exit_code'] = process.returncode
        result['duration_seconds'] = round(time.monotonic() - started, 2)
        output.seek(0)
        text = output.read().decode('utf-8', errors='replace')
        encoding = sys.stdout.encoding or 'utf-8'
        print(text.encode(encoding, errors='backslashreplace').decode(encoding), end='', flush=True)
        return result


def stop(process, job):
    ok = True
    if job:
        try:
            job.close()
        except OSError:
            ok = False
    elif process and os.name != 'nt':
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            ok = False
    if process:
        try:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            ok = False
    return ok
