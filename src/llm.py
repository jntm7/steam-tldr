import json
import os
import signal
import subprocess
import tempfile

# Model to ask through the Claude Code CLI
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-5-5")
TIMEOUT_SECONDS = 120

# A model call that failed in a way worth skipping the game for, not stopping the run
class ModelError(RuntimeError):
    pass

# The model in use, saved next to each written summary
def model_name() -> str:
    return f"claude:{CLAUDE_MODEL}"

# Ask Claude with no tools, in an empty folder and with no piped input, and return its reply text
def complete(prompt: str) -> str:
    with tempfile.TemporaryDirectory() as folder:
        try:
            process = subprocess.Popen(["claude", "-p", "--model", CLAUDE_MODEL, "--tools", "", "--output-format", "json",
                                        "--no-session-persistence", "--strict-mcp-config", prompt],
                                       cwd=folder, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, start_new_session=True)
        except FileNotFoundError as error:
            raise ModelError("The claude command was not found; install Claude Code and log in first") from error
        try:
            stdout, stderr = process.communicate(timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as error:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise ModelError(f"Claude took longer than {TIMEOUT_SECONDS}s") from error
    try:
        reply = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise ModelError(f"Claude returned no JSON: {(stderr or stdout)[-300:].strip()}") from error
    if reply.get("is_error") or not reply.get("result"):
        raise ModelError(f"Claude returned an error: {str(reply.get('result'))[:300]}")
    return reply["result"]
