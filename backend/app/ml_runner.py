"""Internal process boundary: receives only worker-generated private JSON paths."""
import json
import sys
from pathlib import Path

def process_request(request_path):
    import time
    request=json.loads(Path(request_path).read_text())
    started=time.monotonic()
    progress_path=Path(request['progress_path'])
    cancel_path=Path(request['cancel_path'])
    def progress(completed,total,stage):
        temporary=progress_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(dict(completed_steps=int(completed),total_steps=int(total),stage=stage)))
        temporary.replace(progress_path)
    try:
        if request['kind']=='protect':
            from .ml.defenders import protect
            output=protect(request['clean_path'],request['mask_path'],request['output_path'],request['config'],progress,lambda:cancel_path.exists())
        else:
            from .ml.editor import edit_pair
            output=edit_pair(request['clean_path'],request['protected_path'],request['mask_path'],request['output_dir'],request['config'],progress,lambda:cancel_path.exists())
        result=dict(ok=True,output=output)
    except BaseException as exc:
        import traceback
        traceback.print_exc()
        name=type(exc).__name__
        code=getattr(exc,'code','cuda_oom' if 'OutOfMemory' in name or 'out of memory' in str(exc).lower() else 'model_execution_failed')
        messages={'cuda_oom':'GPU memory was exhausted. No protection result was accepted. Close other GPU applications or use a larger GPU.','cancelled':'The job was cancelled.','model_unavailable':'Model files or CUDA dependencies are unavailable. Run the environment doctor.'}
        result=dict(ok=False,error_code=code,error_message=messages.get(code,'Model execution failed. Inspect the private worker log for details.'))
    result['runtime_seconds']=time.monotonic()-started
    destination=Path(request['result_path'])
    temporary=destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(result,default=str))
    temporary.replace(destination)

def main():
    if sys.argv[1:]!=['--serve']:
        process_request(sys.argv[1])
        return
    import os
    import threading
    import time
    import psutil
    # Native Windows venv launchers add an intermediate process. Watch the
    # actual worker PID rather than that launcher, which can outlive a crash.
    parent=psutil.Process(int(os.environ.get('IMAGESHIELD_WORKER_PID',os.getppid())))
    parent_created=parent.create_time()
    def watch_parent():
        while True:
            time.sleep(2)
            try:
                if not parent.is_running() or parent.create_time()!=parent_created:
                    os._exit(1)
            except psutil.Error:
                os._exit(1)
    threading.Thread(target=watch_parent,daemon=True).start()
    for line in sys.stdin:
        if line.strip():
            process_request(line.strip())

if __name__=='__main__':
    main()
