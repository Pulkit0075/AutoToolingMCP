from __future__ import annotations

import asyncio, logging, os, signal, subprocess, sys, threading, time
from typing import Dict, Optional, Union

from interactive_shell_utils import looks_like_repl, contains_prompt
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("autoMcp")
RESTART_CODE = 87 

# ────────────────────────── config & logger ──────────────────────────────
DEFAULT_TIMEOUT = 60           # seconds
LOG_PATH = "bash_safe.log"

_logger = logging.getLogger("bash_safe")
if not _logger.handlers:
    _logger.setLevel(logging.DEBUG)
    h = logging.FileHandler(LOG_PATH, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _logger.addHandler(h)

# ────────────────────────── helpers ──────────────────────────────────────
def _kill_tree(pid: int) -> None:
    """Best-effort terminate *pid* and its children (cross-platform)."""
    if os.name == "nt":
        subprocess.call(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        try:
            os.killpg(pid, signal.SIGTERM)
        except OSError:
            pass


def _start_process(command: str) -> subprocess.Popen:
    """Spawn *command* in its own process group/session."""
    if os.name == "nt":
        return subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        return subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )


def _pump(proc: subprocess.Popen, buf: list[str]) -> None:
    """Background thread to mirror subprocess output to log."""
    with proc.stdout:
        for line in iter(proc.stdout.readline, ""):
            buf.append(line)
            _logger.debug(line.rstrip())

# ────────────────────────── MCP tools ────────────────────────────────────
@mcp.tool()
async def bash_safe(command: str, *, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Union[str, int, None]]:
    """
    Run *command* with strict timeout and full logging.
    """
    if timeout <= 0:
        warn = "Timeout must be positive seconds."
        _logger.error(warn)
        return {"output": "", "warning": warn, "returncode": None}

    reason = looks_like_repl(command)
    if reason:
        _logger.warning("Blocked: %s", reason)
        return {"output": "", "warning": f"Blocked: {reason}", "returncode": None}

    _logger.info("EXEC ➜ %s", command)
    proc = _start_process(command)
    lines: list[str] = []
    threading.Thread(target=_pump, args=(proc, lines), daemon=True).start()

    start = time.time()
    warn: Optional[str] = None

    while proc.poll() is None:
        await asyncio.sleep(0.05)
        if time.time() - start > timeout:
            warn = f"Process exceeded {timeout}s – terminating."
            _logger.warning(warn)
            if os.name == "nt":
                proc.send_signal(signal.CTRL_BREAK_EVENT)
                try:
                    proc.wait(5)
                except subprocess.TimeoutExpired:
                    _kill_tree(proc.pid)
            else:
                _kill_tree(proc.pid)
            proc.wait()
            break

    output = "".join(lines).strip()
    if not warn and contains_prompt(output):
        warn = "Output ends with a prompt-like string."
        _logger.warning(warn)

    return {
        "output": output,
        "warning": warn,
        "returncode": proc.returncode if proc.returncode is not None else -1,
    }


@mcp.tool()
async def pyEdit(filepath: str, content: str | None = None) -> str:
    """Read or write a Python file."""
    try:
        if content is None:
            if not os.path.isfile(filepath):
                return f"Error: File '{filepath}' does not exist."
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to '{filepath}'."
    except Exception as e:
        return f"Exception: {e}"


@mcp.tool()
async def request_restart() -> str:
    """
    Tell the wrapper to respawn this worker.

    We first *return* a confirmation string, then—on a background thread—sleep
    200 ms and exit with the reserved code so the wrapper can restart us.
    """
    def _delayed_exit():
        time.sleep(0.2)
        # flush just in case
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(RESTART_CODE)        # immediate, cross-platform

    threading.Thread(target=_delayed_exit, daemon=True).start()

    # This string reaches the Claude desktop before the process dies
    return "✅  Restart requested – worker will be back in a second."

# ────────────────────────── bootstrap ────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")
