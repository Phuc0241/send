import shutil
import os
import time

SRC_APP = r"static\app.js"
SRC_IDX = r"static\index.html"

DEST_DIRS = [
    r"dist\SendAnywhere\_internal\static",
    r"dist (desktop app hoạt động tốt nhưng chưa hoàn hảo)\SendAnywhere\_internal\static",
    r"dist (hoạt động hoàn hảo có load trang và có thông báo)\SendAnywhere\_internal\static",
    r"dist1\SendAnywhere\_internal\static",
    r"dist2\SendAnywhere\_internal\static",
    r"dist3\SendAnywhere\_internal\static",
    r"nodist\SendAnywhere\_internal\static"
]

print("Starting Sync...")
for d in DEST_DIRS:
    if not os.path.exists(d):
        print(f"SKIPPED (Not found): {d}")
        continue
        
    try:
        shutil.copy2(SRC_APP, os.path.join(d, "app.js"))
        shutil.copy2(SRC_IDX, os.path.join(d, "index.html"))
        print(f"SUCCESS: {d}")
    except PermissionError:
        print(f"LOCKED (App Open?): {d}")
    except Exception as e:
        print(f"ERROR {d}: {e}")

print("Sync Finished.")
