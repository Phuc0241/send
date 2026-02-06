"""
Signaling Server - WebSocket server for pair code and WebRTC signaling
Handles client pairing, SDP exchange, and LAN discovery coordination
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Set
import json
import random
import string
from datetime import datetime, timedelta
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SIGNALING_HOST, SIGNALING_PORT, PAIR_CODE_LENGTH, PAIR_CODE_EXPIRY

app = FastAPI(title="Send Anywhere Signaling Server")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active connections: {pair_code: {sender: WebSocket, receiver: WebSocket}}
rooms: Dict[str, Dict[str, WebSocket]] = {}

# Pair code metadata: {pair_code: {created_at, transfer_id, manifest}}
pair_codes: Dict[str, dict] = {}

def generate_pair_code() -> str:
    """Generate a unique 6-digit pair code"""
    while True:
        code = ''.join(random.choices(string.digits, k=PAIR_CODE_LENGTH))
        if code not in pair_codes:
            return code

def cleanup_expired_codes():
    """Remove expired pair codes"""
    now = datetime.now()
    expired = []
    
    for code, data in pair_codes.items():
        created_at = data.get('created_at')
        if created_at and (now - created_at).total_seconds() > PAIR_CODE_EXPIRY:
            expired.append(code)
    
    for code in expired:
        del pair_codes[code]
        if code in rooms:
            del rooms[code]
    
    return len(expired)

@app.post("/pair/create")
async def create_pair_code(transfer_id: str, manifest: str):
    """
    Create a new pair code for a transfer
    Returns the pair code to share with receiver
    """
    try:
        # Cleanup expired codes first
        cleanup_expired_codes()
        
        # Generate unique code
        code = generate_pair_code()
        
        # Store pair code metadata
        pair_codes[code] = {
            'transfer_id': transfer_id,
            'manifest': json.loads(manifest),
            'created_at': datetime.now(),
            'status': 'waiting'
        }
        
        return {
            "pair_code": code,
            "transfer_id": transfer_id,
            "expires_in": PAIR_CODE_EXPIRY
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create pair code: {str(e)}")

@app.get("/pair/{code}/info")
async def get_pair_info(code: str):
    """Get information about a pair code"""
    cleanup_expired_codes()
    
    if code not in pair_codes:
        raise HTTPException(status_code=404, detail="Pair code not found or expired")
    
    data = pair_codes[code]
    age = (datetime.now() - data['created_at']).total_seconds()
    
    return {
        "pair_code": code,
        "transfer_id": data['transfer_id'],
        "manifest": data['manifest'],
        "status": data['status'],
        "expires_in": max(0, PAIR_CODE_EXPIRY - int(age))
    }

@app.websocket("/ws/{code}/{role}")
async def websocket_endpoint(websocket: WebSocket, code: str, role: str):
    """
    WebSocket endpoint for signaling
    role: 'sender' or 'receiver'
    """
    await websocket.accept()
    
    # Validate pair code
    if code not in pair_codes:
        await websocket.send_json({
            "type": "error",
            "message": "Invalid or expired pair code"
        })
        await websocket.close()
        return
    
    # Validate role
    if role not in ['sender', 'receiver']:
        await websocket.send_json({
            "type": "error",
            "message": "Invalid role. Must be 'sender' or 'receiver'"
        })
        await websocket.close()
        return
    
    # Create room if not exists
    if code not in rooms:
        rooms[code] = {}
    
    # Add connection to room
    rooms[code][role] = websocket
    
    # Send connection confirmation
    await websocket.send_json({
        "type": "connected",
        "role": role,
        "pair_code": code
    })
    
    # Notify peer if both connected
    if 'sender' in rooms[code] and 'receiver' in rooms[code]:
        pair_codes[code]['status'] = 'paired'
        
        # Notify both parties
        await rooms[code]['sender'].send_json({
            "type": "peer_connected",
            "peer_role": "receiver"
        })
        await rooms[code]['receiver'].send_json({
            "type": "peer_connected",
            "peer_role": "sender",
            "manifest": pair_codes[code]['manifest']
        })
    
    try:
        # Handle messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Forward message to peer
            peer_role = 'receiver' if role == 'sender' else 'sender'
            
            if peer_role in rooms[code]:
                await rooms[code][peer_role].send_json(message)
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": "Peer not connected"
                })
    
    except WebSocketDisconnect:
        # Remove from room
        if code in rooms and role in rooms[code]:
            del rooms[code][role]
        
        # Notify peer about disconnection
        peer_role = 'receiver' if role == 'sender' else 'sender'
        if code in rooms and peer_role in rooms[code]:
            await rooms[code][peer_role].send_json({
                "type": "peer_disconnected",
                "peer_role": role
            })
        
        # Clean up empty rooms
        if code in rooms and len(rooms[code]) == 0:
            del rooms[code]

@app.get("/stats")
async def get_stats():
    """Get server statistics"""
    cleanup_expired_codes()
    
    return {
        "active_pairs": len(rooms),
        "total_pair_codes": len(pair_codes),
        "active_connections": sum(len(room) for room in rooms.values())
    }

@app.head("/")
async def root_head():
    """HEAD endpoint for UptimeRobot"""
    return Response(status_code=200)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Send Anywhere Signaling Server",
        "status": "running",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Starting Signaling Server on {SIGNALING_HOST}:{SIGNALING_PORT}")
    print(f"🔢 Pair code length: {PAIR_CODE_LENGTH} digits")
    print(f"⏰ Pair code expiry: {PAIR_CODE_EXPIRY} seconds")
    uvicorn.run(app, host=SIGNALING_HOST, port=SIGNALING_PORT)
