"""CPU-only coverage for the persistent process and private result protocol."""
import json
import os
import subprocess
import sys
import time
import types
from pathlib import Path

import pytest

from backend.app import ml_runner, ml_runtime


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    real_popen = subprocess.Popen
    launched = []
    helper = (
        "import sys,json,os; from pathlib import Path\n"
        "for line in sys.stdin:\n"
        " p=Path(line.strip()); p.with_suffix('.seen').write_text(json.dumps({'pid':os.getpid(),'request':str(p)}))\n"
    )

    def launch(command, **kwargs):
        assert command[-1] == '--serve'
        assert kwargs['env']['IMAGESHIELD_WORKER_PID'] == str(os.getpid())
        child = real_popen([sys.executable, '-u', '-c', helper], **kwargs)
        launched.append(child)
        return child

    monkeypatch.setattr(ml_runtime.subprocess, 'Popen', launch)
    monkeypatch.setattr(ml_runtime, 'DATA', tmp_path)
    instance = ml_runtime.MLRuntime()
    yield instance, launched
    instance.close()


def await_request(path):
    seen = path.with_suffix('.seen')
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if seen.exists():
            return json.loads(seen.read_text())
        time.sleep(.01)
    pytest.fail('Protocol helper did not receive the request')


def test_reuses_child_for_multiple_requests(runtime, tmp_path):
    instance, launched = runtime
    first = tmp_path / 'first.json'
    second = tmp_path / 'second.json'
    child = instance.submit(first)
    first_pid = await_request(first)['pid']
    assert instance.submit(second) is child
    assert await_request(second)['pid'] == first_pid
    assert len(launched) == 1
    instance.close()
    assert child.poll() == 0
    assert instance.process is None and instance.log is None


def test_restarts_dead_child(runtime, tmp_path):
    instance, launched = runtime
    first = tmp_path / 'first.json'
    dead = instance.submit(first)
    old_pid = await_request(first)['pid']
    dead.kill()
    dead.wait(timeout=5)
    second = tmp_path / 'second.json'
    replacement = instance.submit(second)
    assert replacement is not dead
    assert await_request(second)['pid'] != old_pid
    assert len(launched) == 2
    assert dead.stdin.closed


def test_idle_shutdown_tracks_latest_completion(runtime, tmp_path, monkeypatch):
    instance, _ = runtime
    request = tmp_path / 'first.json'
    child = instance.submit(request)
    await_request(request)
    now = [100.0]
    monkeypatch.setattr(ml_runtime.time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(ml_runtime.settings, 'model_idle_seconds', 10)
    instance.mark_idle()
    now[0] = 109
    instance.trim_idle()
    assert instance.process is child
    instance.mark_idle()
    now[0] = 118
    instance.trim_idle()
    assert instance.process is child
    now[0] = 120
    instance.trim_idle()
    assert instance.process is None and instance.log is None
    assert child.poll() == 0


@pytest.fixture
def request_file(tmp_path):
    request = dict(kind='protect', clean_path='clean.png', mask_path='mask.png',
                   output_path='protected.png', protected_path='protected.png',
                   output_dir=str(tmp_path), config={'seed': 42},
                   progress_path=str(tmp_path / 'progress.json'),
                   cancel_path=str(tmp_path / 'cancel'),
                   result_path=str(tmp_path / 'result.json'))
    path = tmp_path / 'request.json'
    path.write_text(json.dumps(request))
    return path, request


def test_runner_publishes_complete_result_and_progress_atomically(request_file, monkeypatch):
    path, request = request_file
    replacements = []
    real_replace = Path.replace

    def checked_replace(source, destination):
        destination = Path(destination)
        assert source.suffix == '.tmp'
        assert not destination.exists()
        replacements.append((destination.name, json.loads(source.read_text())))
        return real_replace(source, destination)

    def protect(clean, mask, output, config, progress, cancelled):
        assert (clean, mask, output, config) == ('clean.png', 'mask.png', 'protected.png', {'seed': 42})
        assert cancelled() is False
        Path(request['cancel_path']).touch()
        assert cancelled() is True
        progress(2, 3, 'protecting')
        return {'path': Path(output)}

    monkeypatch.setitem(sys.modules, 'backend.app.ml.defenders', types.SimpleNamespace(protect=protect))
    monkeypatch.setattr(Path, 'replace', checked_replace)
    ml_runner.process_request(path)
    assert [name for name, _ in replacements] == ['progress.json', 'result.json']
    assert replacements[0][1] == dict(completed_steps=2, total_steps=3, stage='protecting')
    result = json.loads(Path(request['result_path']).read_text())
    assert result['ok'] is True and result['output'] == {'path': 'protected.png'}
    assert result['runtime_seconds'] >= 0
    assert not list(path.parent.glob('*.tmp'))


@pytest.mark.parametrize('error,code', [(RuntimeError('CUDA out of memory: private details'), 'cuda_oom'),
                                        (ValueError('private filesystem details'), 'model_execution_failed')])
def test_runner_publishes_safe_error_envelope(request_file, monkeypatch, error, code):
    path, request = request_file

    def fail(*args):
        raise error

    monkeypatch.setitem(sys.modules, 'backend.app.ml.defenders', types.SimpleNamespace(protect=fail))
    ml_runner.process_request(path)
    result = json.loads(Path(request['result_path']).read_text())
    assert result['ok'] is False
    assert result['error_code'] == code
    assert str(error) not in result['error_message']
    assert result['runtime_seconds'] >= 0
    assert 'output' not in result
    assert not Path(request['result_path']).with_suffix('.tmp').exists()


def test_runner_dispatches_edit_pair(request_file, monkeypatch):
    path, request = request_file
    request['kind'] = 'edit'
    path.write_text(json.dumps(request))
    calls = []

    def edit_pair(*args):
        calls.append(args)
        return {'clean': 'clean-edit.png', 'protected': 'protected-edit.png'}

    monkeypatch.setitem(sys.modules, 'backend.app.ml.editor', types.SimpleNamespace(edit_pair=edit_pair))
    ml_runner.process_request(path)
    assert calls[0][:5] == ('clean.png', 'protected.png', 'mask.png', request['output_dir'], {'seed': 42})
    result = json.loads(Path(request['result_path']).read_text())
    assert result['ok'] is True
    assert result['output']['protected'] == 'protected-edit.png'


@pytest.mark.skipif(os.name != 'nt', reason='Windows launcher process-tree regression')
def test_forced_close_terminates_launcher_and_sleeping_descendants(tmp_path, monkeypatch):
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    ready = tmp_path / 'sleeping.seen'
    helper = (
        "import os,sys,json,time,subprocess; from pathlib import Path; "
        "child=subprocess.Popen([sys._base_executable,'-c','import time; time.sleep(120)']); "
        "target=Path(sys.argv[1]); temporary=target.with_suffix('.tmp'); "
        "temporary.write_text(json.dumps({'parent':os.getpid(),'child':child.pid})); "
        "temporary.replace(target); time.sleep(120)"
    )
    real_popen = subprocess.Popen
    launched = []

    def launch(command, **kwargs):
        if command[-1] == '--serve':
            assert kwargs['env']['IMAGESHIELD_WORKER_PID'] == str(os.getpid())
            process = real_popen([sys.executable, '-u', '-c', helper, str(ready)], **kwargs)
            launched.append(process)
            return process
        return real_popen(command, **kwargs)

    monkeypatch.setattr(ml_runtime.subprocess, 'Popen', launch)
    monkeypatch.setattr(ml_runtime, 'DATA', tmp_path)
    instance = ml_runtime.MLRuntime()
    handles = []
    try:
        process = instance.submit(tmp_path / 'sleeping.json')
        pids = await_request(tmp_path / 'sleeping.json')
        # Retain process handles before close: PID reuse cannot cause a false result.
        for pid in (pids['parent'], pids['child']):
            handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE only
            assert handle, ctypes.get_last_error()
            handles.append(handle)
            assert kernel.WaitForSingleObject(handle, 0) == 258  # WAIT_TIMEOUT
        instance.close()  # stdin EOF is ignored, requiring forced tree shutdown.
        assert process.poll() is not None
        assert instance.process is None and instance.log is None
        for handle in handles:
            assert kernel.WaitForSingleObject(handle, 5000) == 0  # WAIT_OBJECT_0
    finally:
        for process in launched:
            if process.poll() is None:
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
                process.wait(timeout=10)
        for handle in handles:
            kernel.CloseHandle(handle)
        instance.close()
