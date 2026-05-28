# Futra Dashboard API
# Shared MT5 data cache (updated by background thread, read by API routes)
import threading
from typing import Optional

_mt5_lock = threading.Lock()
_mt5_cache = {
    "positions": [],
    "account": None,
    "last_update": None,
}
