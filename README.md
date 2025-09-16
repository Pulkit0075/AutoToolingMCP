# AutoToolMcp

Lightweight MCP worker exposing safe shell execution and file editing tools for use with Claude Desktop.

Contents
- [autoMcp.py](autoMcp.py) — MCP server with tools: `bash_safe`, `pyEdit`, `request_restart`.
- [launch_worker.py](launch_worker.py) — wrapper that respawns the worker when `request_restart()` asks for it.
- [interactive_shell_utils.py](interactive_shell_utils.py) — helpers: `looks_like_repl`, `contains_prompt`.
- [pyproject.toml](pyproject.toml), [requirements.txt](requirements.txt)

Prerequisites
- Python 3.13 (see `.python-version`)
- Install dependencies:
```sh
pip install -r requirements.txt
# or if using pyproject:
pip install ".[]"  # adjust per your packaging workflow
```

Running locally
- Run the worker directly (for testing):
```sh
python autoMcp.py
```
- Recommended for use with Claude Desktop: run the wrapper so `request_restart()` causes a respawn:
```sh
python launch_worker.py
```

Connecting to Claude Desktop
- Create a JSON launcher entry for Claude Desktop that runs the wrapper script and uses stdio transport.
- Example JSON (save as `autotoolmcp.json` and point Claude Desktop at it). Adjust `python` path and `cwd` to match your environment:

```json
{
  "name": "AutoToolMCP",
  "cwd": "C:\\Users\\[username]\\Desktop\\AutoToolMcp",
  "command": "python",
  "args": ["launch_worker.py"],
  "transport": "stdio"
}
```

Notes:
- The wrapper `launch_worker.py` will run the MCP worker and stream stdout/stderr; it will restart the worker if the worker exits with the reserved exit code returned by the [`autoMcp.request_restart`](autoMcp.py) tool.
- The worker exposes the tools described below via MCP/stdio.

Important: restart Claude Desktop when you add a new tool
- When you add a new `@mcp.tool()` to `autoMcp.py`, Claude Desktop must be restarted (or the Claude Desktop tools list reloaded) to pick up the new tool. The worker processes are discovered/loaded by the Claude Desktop client at startup; adding a tool to the source does not automatically update the client view.
- You can trigger a controlled worker restart from within Claude by calling the [`autoMcp.request_restart`](autoMcp.py) tool — the wrapper will respawn the worker — but the Claude Desktop client itself must still be restarted/reloaded to refresh the tool list.

Provided tools (main ones)
- [`autoMcp.bash_safe`](autoMcp.py) — run shell commands with timeout and prompt-detection (`interactive_shell_utils.looks_like_repl`, `interactive_shell_utils.contains_prompt`).
- [`autoMcp.pyEdit`](autoMcp.py) — read/write Python files.
- [`autoMcp.request_restart`](autoMcp.py) — request the wrapper to restart this worker.


Example Claude prompt that creates a tool
Use this example prompt in Claude Desktop to request a new MCP tool. Claude should return only the Python function (ready to paste into `autoMcp.py`) inside a fenced code block. After pasting the tool into `autoMcp.py`, restart Claude Desktop so the new tool is discovered.

Example prompt to paste into Claude Desktop:

```
Please generate a single Python async function decorated with @mcp.tool() suitable for adding directly into autoMcp.py.
- Keep imports unchanged; assume `mcp` is already defined.
- Name the tool `count_lines`.
- Signature: async def count_lines(filepath: str) -> dict[str, object]
- Behavior: if the file does not exist, return {"error": "File not found", "count": None}.
  Otherwise open the file (utf-8), count the number of non-empty lines, and return {"error": None, "count": <int>}.
- Do minimal error handling and return any exception message in "error".
- Return only the function code inside a Python fenced code block (no explanation).
```

Quick example of the expected tool code that Claude should return (for reference):

```python
@mcp.tool()
async def count_lines(filepath: str) -> dict[str, object]:
    """Return count of non-empty lines in filepath."""
    try:
        if not os.path.isfile(filepath):
            return {"error": "File not found", "count": None}
        with open(filepath, "r", encoding="utf-8") as f:
            count = sum(1 for line in f if line.strip())
        return {"error": None, "count": count}
    except Exception as e:
        return {"error": str(e), "count": None}
```

Reminder: restart Claude Desktop after adding a new `@mcp.tool()` to `autoMcp.py` so the client loads the updated tool list.


