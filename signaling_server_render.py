"""
Signaling Server Entry Point for Render.com
"""
import os
import sys

# Ensure backend can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from backend.signaling_server import app
    print("✅ Signaling app imported successfully")
except ImportError as e:
    print(f"❌ Failed to import signaling app: {e}")
    sys.exit(1)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 3000))
    print(f"🚀 Starting Signaling Server on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
