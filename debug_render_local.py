import os
import sys
import importlib

print("="*60)
print("🔍 DEBUGGING RENDER DEPLOYMENT SIMULATION")
print("="*60)

# 1. Simulate Render Environment
print("\n[1] Setting environment variables...")
os.environ["PORT"] = "10000"
print("    PORT = 10000 (Set)")

# 2. Check Paths
print("\n[2] Checking Paths...")
current_dir = os.path.dirname(os.path.abspath(__file__))
print(f"    Current Dir: {current_dir}")
print(f"    sys.path[0]: {sys.path[0]}")

# 3. Test Config Import
print("\n[3] Testing Config Import...")
try:
    import config
    print("    ✅ 'import config' successful")
    print(f"    UPLOAD_DIR: {config.UPLOAD_DIR}")
    print(f"    TEMP_DIR: {config.TEMP_DIR}")
except Exception as e:
    print(f"    ❌ FAIL: {e}")
    sys.exit(1)

# 4. Test Backend Import
print("\n[4] Testing Backend Package...")
try:
    import backend
    print("    ✅ 'import backend' successful")
except Exception as e:
    print(f"    ❌ FAIL: {e}")

# 5. Test Relay Server Import (simulating relay_server_render.py)
print("\n[5] Testing Relay Server Import...")
try:
    # Simulate what `from backend.relay_server import app` does
    import backend.relay_server
    print("    ✅ 'import backend.relay_server' successful")
    
    # Check if app is created
    if hasattr(backend.relay_server, 'app'):
        print("    ✅ 'app' object found")
    else:
        print("    ❌ 'app' object MISSING")

except Exception as e:
    print(f"    ❌ FAIL: {e}")
    # Print detailed traceback
    import traceback
    traceback.print_exc()

# 6. Test Signaling Server Import (simulating signaling_server_render.py)
print("\n[6] Testing Signaling Server Import...")
try:
    import backend.signaling_server
    print("    ✅ 'import backend.signaling_server' successful")
    
    if hasattr(backend.signaling_server, 'app'):
        print("    ✅ 'app' object found")
    else:
        print("    ❌ 'app' object MISSING")

except Exception as e:
    print(f"    ❌ FAIL: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("✅ SIMULATION COMPLETE")
print("If all checks passed, the code itself is likely fine.")
print("The issue might be network binding or UptimeRobot configuration.")
print("="*60)
