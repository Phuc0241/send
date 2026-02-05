"""
Sender CLI - Command-line tool for sending files/folders
"""
import asyncio
import sys
import os
from pathlib import Path
import aiohttp
import json
from tqdm import tqdm

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import SIGNALING_HOST, SIGNALING_PORT, LAN_DISCOVERY_PORT
from engine.chunk_manager import ChunkManager, format_size
from engine.transfer_engine import TransferEngine
from engine.lan_transfer import LANTransferServer

class SenderCLI:
    """Command-line sender application"""
    
    def __init__(self):
        self.signaling_url = f"http://{SIGNALING_HOST}:{SIGNALING_PORT}"
        self.chunk_manager = ChunkManager(mode='relay')
        self.transfer_engine = TransferEngine(mode='relay')
    
    async def send_file(self, file_path: str, mode: str = 'relay'):
        """Send a file or folder"""
        
        # Validate path
        path = Path(file_path)
        if not path.exists():
            print(f"❌ Path not found: {file_path}")
            return
        
        # Create manifest
        print(f"📦 Creating manifest...")
        if path.is_file():
            manifest = self.chunk_manager.create_file_manifest(str(path))
            print(f"📄 File: {manifest['fileName']}")
            print(f"📦 Size: {format_size(manifest['size'])}")
            print(f"🔢 Chunks: {manifest['totalChunks']}")
        else:
            manifest = self.chunk_manager.create_folder_manifest(str(path))
            print(f"📁 Folder: {manifest['folderName']}")
            print(f"📦 Total Size: {format_size(manifest['totalSize'])}")
            print(f"📄 Files: {manifest['totalFiles']}")
            print(f"🔢 Total Chunks: {sum(f['totalChunks'] for f in manifest['files'])}")
        
        # Generate transfer ID
        import uuid
        transfer_id = str(uuid.uuid4())
        
        # Create pair code
        print(f"\n🔗 Creating pair code...")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.signaling_url}/pair/create",
                params={
                    'transfer_id': transfer_id,
                    'manifest': json.dumps(manifest)
                }
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    pair_code = result['pair_code']
                    print(f"\n{'='*50}")
                    print(f"🔢 PAIR CODE: {pair_code}")
                    print(f"{'='*50}")
                    print(f"⏰ Expires in: {result['expires_in']} seconds")
                    print(f"\n👉 Share this code with the receiver!")
                else:
                    print(f"❌ Failed to create pair code: {await resp.text()}")
                    return
        
        # Choose transfer mode
        if mode == 'lan':
            await self._send_via_lan(manifest, pair_code)
        else:
            await self._send_via_relay(transfer_id, manifest)
    
    async def _send_via_relay(self, transfer_id: str, manifest: dict):
        """Send via relay server"""
        print(f"\n📡 Mode: RELAY SERVER")
        print(f"⬆️  Uploading chunks...")
        
        # Progress bar
        total_chunks = manifest.get('totalChunks', sum(f['totalChunks'] for f in manifest.get('files', [])))
        pbar = tqdm(total=total_chunks, desc="Uploading", unit="chunk")
        
        def progress_callback(chunk_id, total):
            pbar.update(1)
        
        try:
            await self.transfer_engine.upload_to_relay(transfer_id, manifest, progress_callback)
            pbar.close()
            print(f"\n✅ Upload complete!")
            print(f"📥 Receiver can now download the file")
        except Exception as e:
            pbar.close()
            print(f"\n❌ Upload failed: {e}")
    
    async def _send_via_lan(self, manifest: dict, pair_code: str):
        """Send via LAN direct"""
        print(f"\n🌐 Mode: LAN DIRECT (Fastest!)")
        
        # Start LAN server
        server = LANTransferServer(manifest, port=LAN_DISCOVERY_PORT)
        local_ip = await server.start()
        
        print(f"📡 Server IP: {local_ip}:{LAN_DISCOVERY_PORT}")
        print(f"⏳ Waiting for receiver to connect...")
        print(f"   (Press Ctrl+C to stop)")
        
        try:
            # Keep server running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print(f"\n\n🛑 Server stopped")

async def main():
    """Main entry point"""
    print("=" * 60)
    print("🚀 Send Anywhere - Sender CLI")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python sender_cli.py <file_or_folder_path> [mode]")
        print("\nModes:")
        print("  relay  - Upload to relay server (default)")
        print("  lan    - Direct LAN transfer (fastest)")
        print("\nExamples:")
        print("  python sender_cli.py myfile.zip")
        print("  python sender_cli.py myfolder/ lan")
        sys.exit(1)
    
    file_path = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else 'relay'
    
    sender = SenderCLI()
    await sender.send_file(file_path, mode)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
