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
    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[RotatingFileHandlerSafe(CONFIG_PATHS["log_file"])]
    )
    return logging.getLogger("mint-dynamic-theme")

@contextmanager
def pid_file_manager(pid_path: str):
    """Context manager para gestionar el archivo PID de forma segura."""
    log = logging.getLogger("mint-dynamic-theme")
    try:
        with open(pid_path, 'w') as f:
            f.write(str(os.getpid()))
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
