"""launch_worker.py
Wrapper that respawns *autoMcp.py* whenever it exits with code 87.
Run **this** from the Claude desktop app.
"""

import subprocess, sys, threading

PY            = sys.executable
WORKER_MODULE = "autoMcp"    # adjust if filename differs
CMD           = [PY, "-m", WORKER_MODULE]
RESTART_CODE  = 87                 # reserved by request_restart()

def _pipe(src, dst):
    for chunk in iter(src.readline, b""):
        dst.buffer.write(chunk)
        dst.flush()

while True:
    proc = subprocess.Popen(CMD, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    threading.Thread(target=_pipe, args=(proc.stdout, sys.stdout), daemon=True).start()
    threading.Thread(target=_pipe, args=(proc.stderr, sys.stderr), daemon=True).start()

    if proc.wait() != RESTART_CODE:
        sys.exit(proc.returncode)
    # otherwise loop to respawn
