"""
Relay Server Entry Point for Render.com
"""
import os
import sys

# Ensure backend can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from backend.relay_server import app
    print("✅ Relay app imported successfully")
except ImportError as e:
    print(f"❌ Failed to import relay app: {e}")
    sys.exit(1)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting Relay Server on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
