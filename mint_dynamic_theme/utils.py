import os
import sys
import logging
import signal
from contextlib import contextmanager
from .config import CONFIG_PATHS, MAX_LOG_SIZE

class RotatingFileHandlerSafe(logging.Handler):
    """Handler que limita el tamaño del log"""
    def __init__(self, filename, max_bytes=MAX_LOG_SIZE):
        super().__init__()
        self.filename = filename
        self.max_bytes = max_bytes

    def emit(self, record):
        try:
            if os.path.exists(self.filename) and os.path.getsize(self.filename) > self.max_bytes:
                backup = f"{self.filename}.old"
                if os.path.exists(backup):
                    os.remove(backup)
                os.rename(self.filename, backup)

            msg = self.format(record)
            with open(self.filename, 'a') as f:
                f.write(msg + '\n')
        except Exception:
            pass

def setup_logging():
    level_name = os.getenv("MDT_LOG_LEVEL", "ERROR").upper()
    level = getattr(logging, level_name, logging.ERROR)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[RotatingFileHandlerSafe(CONFIG_PATHS["log_file"])],
    )
    return logging.getLogger("mint-dynamic-theme")

@contextmanager
def pid_file_manager(pid_path: str):
    """Context manager para gestionar el archivo PID de forma segura."""
    log = logging.getLogger("mint-dynamic-theme")
    try:
        fd = os.open(pid_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(str(os.getpid()))
        try:
            os.chmod(pid_path, 0o600)
        except OSError:
            pass
        yield pid_path
    finally:
        try:
            if os.path.exists(pid_path):
                os.remove(pid_path)
        except OSError as e:
            log.error(f"Error eliminando PID file: {e}")

def is_pid_running(pid: int) -> bool:
    """Verifica si un PID está corriendo."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True # Existe pero sin permisos
    except Exception:
        return False

def is_mdt_process(pid: int) -> bool:
    """Verifica si el PID corresponde realmente al daemon mdt.

    Evita matar un proceso ajeno cuyo PID haya sido reciclado por el sistema.
    """
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            raw = f.read().decode(errors="replace")
        argv = raw.split("\x00")
        if not argv or not argv[0]:
            return False
        base = os.path.basename(argv[0])
        is_console = base == "mdt"
        is_python_module = base in ("python", "python3") and any(
            "mint_dynamic_theme" in arg for arg in argv[1:]
        )
        return is_console or is_python_module
    except (OSError, ValueError):
        return False

def get_daemon_status() -> dict:
    pid_file = CONFIG_PATHS["pid_file"]
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                content = f.read().strip()
                if not content:
                     return {"status": "stopped", "pid": None}
                pid = int(content)

            status = "running" if is_pid_running(pid) else "dead"
            return {"status": status, "pid": pid}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    else:
        return {"status": "stopped"}
