import sys, os, time

from app.utils.time_provider import get_current_datetime

now = get_current_datetime().isoformat()
print(f"[{now}] SyncDoc running...")
sys.stdout.flush()
