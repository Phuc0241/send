"""
Signaling Server Entry Point for Render.com
"""
import os
from backend.signaling_server import app
from fastapi.middleware.cors import CORSMiddleware

# Add CORS for desktop app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)
