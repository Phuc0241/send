"""
Receiver CLI - Command-line tool for receiving files/folders
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

from config import SIGNALING_HOST, SIGNALING_PORT
from engine.chunk_manager import ChunkManager, format_size
from engine.transfer_engine import TransferEngine

class ReceiverCLI:
    """Command-line receiver application"""
    
    def __init__(self):
        self.signaling_url = f"http://{SIGNALING_HOST}:{SIGNALING_PORT}"
        self.chunk_manager = ChunkManager(mode='relay')
        self.transfer_engine = TransferEngine(mode='relay')
    
    async def receive_file(self, pair_code: str, output_dir: str = "."):
        """Receive a file using pair code"""
        
        # Get pair info
        print(f"🔍 Looking up pair code: {pair_code}")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.signaling_url}/pair/{pair_code}/info") as resp:
                if resp.status == 200:
                    pair_info = await resp.json()
                else:
                    print(f"❌ Invalid or expired pair code")
                    return
        
        transfer_id = pair_info['transfer_id']
        manifest = pair_info['manifest']
        
        # Display transfer info
        print(f"\n{'='*60}")
        print(f"📥 Transfer Information")
        print(f"{'='*60}")
        
        if 'fileName' in manifest:
            # Single file
            print(f"📄 File: {manifest['fileName']}")
            print(f"📦 Size: {format_size(manifest['size'])}")
            print(f"🔢 Chunks: {manifest['totalChunks']}")
            output_path = os.path.join(output_dir, manifest['fileName'])
        else:
            # Folder
            print(f"📁 Folder: {manifest['folderName']}")
            print(f"📦 Total Size: {format_size(manifest['totalSize'])}")
            print(f"📄 Files: {manifest['totalFiles']}")
            print(f"🔢 Total Chunks: {sum(f['totalChunks'] for f in manifest['files'])}")
            output_path = os.path.join(output_dir, manifest['folderName'])
        
        print(f"💾 Output: {output_path}")
        print(f"⏰ Expires in: {pair_info['expires_in']} seconds")
        
        # Ask for confirmation
        response = input(f"\n📥 Download this file? (y/n): ")
        if response.lower() != 'y':
            print("❌ Download cancelled")
            return
        
        # Download
        await self._download_from_relay(transfer_id, manifest, output_path)
    
    async def _download_from_relay(self, transfer_id: str, manifest: dict, output_path: str):
        """Download from relay server"""
        print(f"\n📡 Mode: RELAY SERVER")
        print(f"⬇️  Downloading chunks...")
        
        # Progress bar
        total_chunks = manifest.get('totalChunks', sum(f['totalChunks'] for f in manifest.get('files', [])))
        pbar = tqdm(total=total_chunks, desc="Downloading", unit="chunk")
        
        def progress_callback(chunk_id, total):
            pbar.update(1)
        
        try:
            await self.transfer_engine.download_from_relay(transfer_id, output_path, progress_callback)
            pbar.close()
            
            # Verify file
            print(f"\n🔍 Verifying integrity...")
            if 'fileName' in manifest:
                # Single file
                if self.chunk_manager.verify_file(output_path, manifest['hash']):
                    print(f"✅ File verified successfully!")
                else:
                    print(f"⚠️  Warning: File hash mismatch")
            else:
                # Folder - verify each file
                verified = 0
                for file_info in manifest['files']:
                    file_path = os.path.join(output_path, file_info['relativePath'])
                    if self.chunk_manager.verify_file(file_path, file_info['hash']):
                        verified += 1
                
                print(f"✅ Verified {verified}/{len(manifest['files'])} files")
            
            print(f"\n✅ Download complete!")
            print(f"📁 Saved to: {output_path}")
        
        except Exception as e:
            pbar.close()
            print(f"\n❌ Download failed: {e}")
    
    async def receive_from_lan(self, server_ip: str, output_dir: str = "."):
        """Receive via LAN direct"""
        print(f"\n🌐 Mode: LAN DIRECT")
        print(f"📡 Connecting to: {server_ip}")
        
        # Get manifest first
        from engine.lan_transfer import LANTransferClient
        client = LANTransferClient(server_ip)
        
        try:
            manifest = await client.get_manifest()
            
            # Display info
            if 'fileName' in manifest:
                print(f"📄 File: {manifest['fileName']}")
                print(f"📦 Size: {format_size(manifest['size'])}")
                output_path = os.path.join(output_dir, manifest['fileName'])
            else:
                print(f"📁 Folder: {manifest['folderName']}")
                print(f"📦 Size: {format_size(manifest['totalSize'])}")
                output_path = os.path.join(output_dir, manifest['folderName'])
            
            # Download
            print(f"\n⬇️  Downloading...")
            total_chunks = manifest.get('totalChunks', sum(f['totalChunks'] for f in manifest.get('files', [])))
            pbar = tqdm(total=total_chunks, desc="Downloading", unit="chunk")
            
            def progress_callback(chunk_id, total):
                pbar.update(1)
            
            await self.transfer_engine.download_from_lan(server_ip, output_path, progress_callback)
            pbar.close()
            
            print(f"\n✅ Download complete!")
            print(f"📁 Saved to: {output_path}")
        
        except Exception as e:
            print(f"❌ Download failed: {e}")

async def main():
    """Main entry point"""
    print("=" * 60)
    print("📥 Send Anywhere - Receiver CLI")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python receiver_cli.py <pair_code> [output_dir]")
        print("  python receiver_cli.py lan <server_ip> [output_dir]")
        print("\nExamples:")
        print("  python receiver_cli.py 123456")
        print("  python receiver_cli.py 123456 downloads/")
        print("  python receiver_cli.py lan 192.168.1.100")
        sys.exit(1)
    
    if sys.argv[1] == 'lan':
        if len(sys.argv) < 3:
            print("❌ Please provide server IP for LAN mode")
            sys.exit(1)
        
        server_ip = sys.argv[2]
        output_dir = sys.argv[3] if len(sys.argv) > 3 else "."
        
        receiver = ReceiverCLI()
        await receiver.receive_from_lan(server_ip, output_dir)
    else:
        pair_code = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "."
        
        receiver = ReceiverCLI()
        await receiver.receive_file(pair_code, output_dir)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
