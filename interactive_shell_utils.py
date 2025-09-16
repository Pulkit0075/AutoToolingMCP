"""interactive_shell_utils.py
Helpers for detecting interactive shells/prompts so tools like *bash_safe*
can refuse or warn when a command would drop into a REPL.
"""

from __future__ import annotations
import os, re, shlex
from typing import Dict, List

# ────────────────────────── heuristics data ──────────────────────────────
INTERACTIVE_SHELLS: Dict[str, str] = {
    # cross-platform
    "python": "Python REPL",
    "python3": "Python REPL",
    "py": "Python REPL",
    "bash": "Bash shell",
    "sh": "POSIX shell",
    "zsh": "Z-shell",
    # Windows
    "cmd": "Windows CMD",
    "powershell": "PowerShell",
    "powershell.exe": "PowerShell",
    "pwsh": "PowerShell (Core)",
}
INTERACTIVE_FLAGS: set[str] = {
    "-i", "--interactive",  # POSIX shells
    "-noexit", "-NoExit",   # PowerShell
}

PROMPT_REGEXES: List[re.Pattern[str]] = [
    re.compile(r">>> ?$"),                  # Python
    re.compile(r"In \[\d+]: ?$"),           # IPython / Jupyter
    re.compile(r".+@.+:\S+\$ ?$"),          # user@host:~$
    re.compile(r"[A-Za-z]:\\.*?> ?$"),      # cmd.exe
    re.compile(r"PS [A-Za-z]:\\.*?> ?$"),   # PowerShell
]

# ────────────────────────── public helpers ───────────────────────────────
def looks_like_repl(command: str) -> str | None:
    """Return a reason string if *command* would likely start a REPL; else None."""
    tokens = shlex.split(command, posix=(os.name != "nt"))
    if not tokens:
        return None

    cmd = tokens[0].lower()
    if cmd in INTERACTIVE_SHELLS:
        if len(tokens) == 1:
            return f"'{cmd}' would start an interactive {INTERACTIVE_SHELLS[cmd]}."
        if tokens[1].lower() in INTERACTIVE_FLAGS:
            return f"'{cmd} {tokens[1]}' requests interactive mode."
    return None


def contains_prompt(text: str) -> bool:
    """True if the *last line* of *text* looks like a shell/REPL prompt."""
    if not text:
        return False
    last = text.rstrip().splitlines()[-1]
    return any(rx.fullmatch(last) for rx in PROMPT_REGEXES)
