"""
Web Server - Serves the static web UI
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import uvicorn
import os

app = FastAPI(title="Send Anywhere Web UI")

# Get static directory path
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

@app.get("/")
async def root():
    """Serve the main HTML page"""
    index_path = os.path.join(static_dir, 'index.html')
    return FileResponse(index_path)

# Mount static files AFTER defining routes
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Serve individual static files at root level for backward compatibility
@app.get("/app.js")
async def serve_app_js():
    return FileResponse(os.path.join(static_dir, 'app.js'), media_type='application/javascript')

@app.get("/test.html")
async def serve_test():
    return FileResponse(os.path.join(static_dir, 'test.html'))

if __name__ == "__main__":
    print("🌐 Starting Web UI Server on http://localhost:5001")
    print("📱 Open your browser and navigate to http://localhost:5001")
    print(f"📁 Serving static files from: {static_dir}")
    uvicorn.run(app, host="0.0.0.0", port=5001)
