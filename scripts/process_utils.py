from __future__ import annotations

import shutil
import subprocess
import sys


_WINDOWS_EXECUTABLE_SHIMS = {
    "pnpm": "pnpm.cmd",
}


def terminate_process(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def resolve_command(command: list[str]) -> tuple[list[str], str]:
    executable = command[0]
    if sys.platform == "win32":
        executable = _WINDOWS_EXECUTABLE_SHIMS.get(executable, executable)

    resolved = shutil.which(executable)
    if not resolved:
        raise FileNotFoundError(executable)

    return [resolved, *command[1:]], executable
