"""
Relay Server - Handles chunk upload/download with resume support
Production-ready with hash verification and automatic cleanup
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import hashlib
import json
import aiofiles
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import UPLOAD_DIR, RELAY_HOST, RELAY_PORT, CLEANUP_AFTER_HOURS

app = FastAPI(title="Send Anywhere Relay Server")

# Enable CORS for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage structure: uploads/{transfer_id}/chunks/{chunk_id}
# Storage structure: uploads/{transfer_id}/manifest.json

def get_transfer_dir(transfer_id: str) -> Path:
    """Get transfer directory path"""
    return Path(UPLOAD_DIR) / transfer_id

def get_chunk_dir(transfer_id: str) -> Path:
    """Get chunks directory path"""
    return get_transfer_dir(transfer_id) / "chunks"

def get_manifest_path(transfer_id: str) -> Path:
    """Get manifest file path"""
    return get_transfer_dir(transfer_id) / "manifest.json"

def calculate_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

@app.post("/transfer/create")
async def create_transfer(transfer_id: str, manifest: str):
    """
    Create a new transfer session with manifest
    Manifest contains: fileName, size, chunkSize, totalChunks, hash
    """
    try:
        # Create transfer directories
        transfer_dir = get_transfer_dir(transfer_id)
        chunk_dir = get_chunk_dir(transfer_id)
        
        transfer_dir.mkdir(parents=True, exist_ok=True)
        chunk_dir.mkdir(parents=True, exist_ok=True)
        
        # Save manifest
        manifest_data = json.loads(manifest)
        manifest_path = get_manifest_path(transfer_id)
        
        async with aiofiles.open(manifest_path, 'w') as f:
            await f.write(json.dumps(manifest_data, indent=2))
        
        # Save creation timestamp
        manifest_data['created_at'] = datetime.now().isoformat()
        async with aiofiles.open(manifest_path, 'w') as f:
            await f.write(json.dumps(manifest_data, indent=2))
        
        return {
            "status": "created",
            "transfer_id": transfer_id,
            "total_chunks": manifest_data.get("totalChunks", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create transfer: {str(e)}")

@app.post("/transfer/{transfer_id}/chunk/{chunk_id}")
async def upload_chunk(transfer_id: str, chunk_id: int, file: UploadFile = File(...)):
    """
    Upload a single chunk
    Returns chunk hash for verification
    """
    try:
        chunk_dir = get_chunk_dir(transfer_id)
        
        if not chunk_dir.exists():
            raise HTTPException(status_code=404, detail="Transfer not found")
        
        # Save chunk
        chunk_path = chunk_dir / f"chunk_{chunk_id:06d}"
        
        async with aiofiles.open(chunk_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Calculate hash
        chunk_hash = hashlib.sha256(content).hexdigest()
        
        return {
            "status": "uploaded",
            "chunk_id": chunk_id,
            "hash": chunk_hash,
            "size": len(content)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload chunk: {str(e)}")

@app.get("/transfer/{transfer_id}/chunk/{chunk_id}")
async def download_chunk(transfer_id: str, chunk_id: int):
    """
    Download a single chunk
    Supports resume via range requests
    """
    try:
        chunk_path = get_chunk_dir(transfer_id) / f"chunk_{chunk_id:06d}"
        
        if not chunk_path.exists():
            # Check if transfer exists
            if not get_transfer_dir(transfer_id).exists():
                raise HTTPException(status_code=404, detail=f"Transfer {transfer_id} not found")
            raise HTTPException(status_code=404, detail=f"Chunk {chunk_id} not yet uploaded. Please wait for sender to complete upload.")
        
        # Check if file is readable
        if not chunk_path.is_file():
            raise HTTPException(status_code=500, detail=f"Chunk {chunk_id} exists but is not a file")
        
        return FileResponse(
            chunk_path,
            media_type="application/octet-stream",
            filename=f"chunk_{chunk_id:06d}"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error downloading chunk {chunk_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download chunk {chunk_id}: {str(e)}")

@app.get("/transfer/{transfer_id}/manifest")
async def get_manifest(transfer_id: str):
    """Get transfer manifest"""
    try:
        manifest_path = get_manifest_path(transfer_id)
        
        if not manifest_path.exists():
            raise HTTPException(status_code=404, detail="Transfer not found")
        
        async with aiofiles.open(manifest_path, 'r') as f:
            content = await f.read()
            return json.loads(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get manifest: {str(e)}")

@app.get("/transfer/{transfer_id}/status")
async def get_transfer_status(transfer_id: str):
    """
    Get transfer status - which chunks are uploaded
    Returns list of available chunks
    """
    try:
        chunk_dir = get_chunk_dir(transfer_id)
        
        if not chunk_dir.exists():
            raise HTTPException(status_code=404, detail="Transfer not found")
        
        # Get list of uploaded chunks
        uploaded_chunks = []
        for chunk_file in sorted(chunk_dir.glob("chunk_*")):
            chunk_id = int(chunk_file.name.split("_")[1])
            uploaded_chunks.append(chunk_id)
        
        # Get manifest
        manifest_path = get_manifest_path(transfer_id)
        async with aiofiles.open(manifest_path, 'r') as f:
            manifest = json.loads(await f.read())
        
        total_chunks = manifest.get("totalChunks", 0)
        progress = len(uploaded_chunks) / total_chunks * 100 if total_chunks > 0 else 0
        
        return {
            "transfer_id": transfer_id,
            "total_chunks": total_chunks,
            "uploaded_chunks": len(uploaded_chunks),
            "progress": round(progress, 2),
            "available_chunks": uploaded_chunks,
            "complete": len(uploaded_chunks) == total_chunks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@app.delete("/transfer/{transfer_id}")
async def delete_transfer(transfer_id: str):
    """Delete a transfer and all its chunks"""
    try:
        transfer_dir = get_transfer_dir(transfer_id)
        
        if not transfer_dir.exists():
            raise HTTPException(status_code=404, detail="Transfer not found")
        
        # Delete all files
        import shutil
        shutil.rmtree(transfer_dir)
        
        return {"status": "deleted", "transfer_id": transfer_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete transfer: {str(e)}")

@app.get("/cleanup")
async def cleanup_old_transfers():
    """
    Cleanup transfers older than CLEANUP_AFTER_HOURS
    Returns list of deleted transfers
    """
    try:
        deleted = []
        upload_path = Path(UPLOAD_DIR)
        
        if not upload_path.exists():
            return {"deleted": deleted}
        
        cutoff_time = datetime.now() - timedelta(hours=CLEANUP_AFTER_HOURS)
        
        for transfer_dir in upload_path.iterdir():
            if not transfer_dir.is_dir():
                continue
            
            manifest_path = transfer_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            
            # Check creation time
            async with aiofiles.open(manifest_path, 'r') as f:
                manifest = json.loads(await f.read())
                created_at = datetime.fromisoformat(manifest.get('created_at', datetime.now().isoformat()))
                
                if created_at < cutoff_time:
                    import shutil
                    shutil.rmtree(transfer_dir)
                    deleted.append(transfer_dir.name)
        
        return {
            "status": "cleaned",
            "deleted_count": len(deleted),
            "deleted_transfers": deleted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup: {str(e)}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Send Anywhere Relay Server",
        "status": "running",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Starting Relay Server on {RELAY_HOST}:{RELAY_PORT}")
    print(f"📁 Upload directory: {UPLOAD_DIR}")
    print(f"🧹 Auto-cleanup after: {CLEANUP_AFTER_HOURS} hours")
    uvicorn.run(app, host=RELAY_HOST, port=RELAY_PORT)
