"""
LAN Transfer - Direct HTTP transfer over local network
Fastest mode: 80-120 MB/s
"""
import asyncio
from aiohttp import web
import socket
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LAN_DISCOVERY_PORT
from engine.chunk_manager import ChunkManager

class LANTransferServer:
    """HTTP server for LAN direct transfer"""
    
    def __init__(self, manifest: dict, port: int = LAN_DISCOVERY_PORT):
        self.manifest = manifest
        self.port = port
        self.chunk_manager = ChunkManager(mode='lan')
        self.app = web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get('/manifest', self.handle_manifest)
        self.app.router.add_get('/chunk/{chunk_id}', self.handle_chunk)
        self.app.router.add_get('/file/{file_index}/chunk/{chunk_id}', self.handle_file_chunk)
    
    async def handle_manifest(self, request):
        """Return transfer manifest"""
        return web.json_response(self.manifest)
    
    async def handle_chunk(self, request):
        """Handle single file chunk download"""
        chunk_id = int(request.match_info['chunk_id'])
        
        # For single file transfers
        if 'filePath' in self.manifest:
            file_path = self.manifest['filePath']
            
            try:
                chunk_data = self.chunk_manager.read_chunk(file_path, chunk_id)
                return web.Response(
                    body=chunk_data,
                    content_type='application/octet-stream',
                    headers={
                        'Content-Disposition': f'attachment; filename="chunk_{chunk_id:06d}"'
                    }
                )
            except Exception as e:
                return web.json_response({'error': str(e)}, status=500)
        
        return web.json_response({'error': 'Invalid request'}, status=400)
    
    async def handle_file_chunk(self, request):
        """Handle folder file chunk download"""
        file_index = int(request.match_info['file_index'])
        chunk_id = int(request.match_info['chunk_id'])
        
        # For folder transfers
        if 'files' in self.manifest:
            if file_index >= len(self.manifest['files']):
                return web.json_response({'error': 'File index out of range'}, status=404)
            
            file_info = self.manifest['files'][file_index]
            file_path = file_info['filePath']
            
            try:
                chunk_data = self.chunk_manager.read_chunk(file_path, chunk_id)
                return web.Response(
                    body=chunk_data,
                    content_type='application/octet-stream',
                    headers={
                        'Content-Disposition': f'attachment; filename="chunk_{chunk_id:06d}"'
                    }
                )
            except Exception as e:
                return web.json_response({'error': str(e)}, status=500)
        
        return web.json_response({'error': 'Invalid request'}, status=400)
    
    def get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            # Create a socket to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"
    
    async def start(self):
        """Start the LAN server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        local_ip = self.get_local_ip()
        print(f"🌐 LAN Server started at http://{local_ip}:{self.port}")
        return local_ip

class LANTransferClient:
    """Client for downloading via LAN"""
    
    def __init__(self, server_ip: str, port: int = LAN_DISCOVERY_PORT):
        self.server_url = f"http://{server_ip}:{port}"
        self.chunk_manager = ChunkManager(mode='lan')
    
    async def get_manifest(self) -> dict:
        """Get manifest from server"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.server_url}/manifest") as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    raise Exception(f"Failed to get manifest: {resp.status}")
    
    async def download_chunk(self, chunk_id: int) -> bytes:
        """Download a single chunk"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.server_url}/chunk/{chunk_id}") as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    raise Exception(f"Failed to download chunk {chunk_id}: {resp.status}")
    
    async def download_file_chunk(self, file_index: int, chunk_id: int) -> bytes:
        """Download a chunk from a specific file in folder transfer"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.server_url}/file/{file_index}/chunk/{chunk_id}") as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    raise Exception(f"Failed to download chunk {chunk_id} from file {file_index}: {resp.status}")

if __name__ == "__main__":
    # Test LAN server
    print("LAN Transfer Module")
    print("Use sender_cli.py or receiver_cli.py for actual transfers")
