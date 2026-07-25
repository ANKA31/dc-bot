import json
import os
import shutil
import threading

from config import DATA_DIR

_locks = {}

def _resolve(path):
    if DATA_DIR and not os.path.isabs(path):
        return os.path.join(DATA_DIR, path)
    return path

def read_json(path, default=None):
    lock = _locks.setdefault(path, threading.Lock())
    with lock:
        try:
            with open(_resolve(path), "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default if default is not None else {}

def write_json(path, data):
    lock = _locks.setdefault(path, threading.Lock())
    resolved = _resolve(path)
    os.makedirs(os.path.dirname(resolved) or ".", exist_ok=True)
    with lock:
        tmp = resolved + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            shutil.move(tmp, resolved)
        except:
            try:
                os.remove(tmp)
            except:
                pass
            raise
