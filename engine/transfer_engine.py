"""
Transfer Engine - Main orchestration for file transfers
Handles mode detection, parallel downloads, and resume logic
"""
import asyncio
import aiohttp
from typing import List, Dict, Optional
from pathlib import Path
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    MAX_PARALLEL_CHUNKS, MIN_PARALLEL_CHUNKS,
    MAX_RETRY_ATTEMPTS, RETRY_DELAY,
    RELAY_HOST, RELAY_PORT
)
from engine.chunk_manager import ChunkManager
from engine.lan_transfer import LANTransferClient

class TransferEngine:
    """Main transfer orchestration engine"""
    
    def __init__(self, mode: str = "relay"):
        """
        Initialize transfer engine
        mode: 'lan', 'webrtc', or 'relay'
        """
        self.mode = mode
        self.chunk_manager = ChunkManager(mode=mode)
        self.parallel_workers = MAX_PARALLEL_CHUNKS
        self.relay_url = f"http://{RELAY_HOST}:{RELAY_PORT}"
    
    async def upload_to_relay(self, transfer_id: str, manifest: dict, progress_callback=None):
        """Upload file/folder to relay server"""
        
        # Create transfer on relay
        async with aiohttp.ClientSession() as session:
            import json
            async with session.post(
                f"{self.relay_url}/transfer/create",
                params={
                    'transfer_id': transfer_id,
                    'manifest': json.dumps(manifest)
                }
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to create transfer: {await resp.text()}")
        
        # Upload chunks
        if 'files' in manifest:
            # Folder transfer
            await self._upload_folder_chunks(transfer_id, manifest, progress_callback)
        else:
            # Single file transfer
            await self._upload_file_chunks(transfer_id, manifest, progress_callback)
    
    async def _upload_file_chunks(self, transfer_id: str, manifest: dict, progress_callback=None):
        """Upload chunks for a single file"""
        file_path = manifest['filePath']
        total_chunks = manifest['totalChunks']
        
        # Upload chunks in parallel
        semaphore = asyncio.Semaphore(self.parallel_workers)
        
        async def upload_chunk(chunk_id: int):
            async with semaphore:
                for attempt in range(MAX_RETRY_ATTEMPTS):
                    try:
                        chunk_data = self.chunk_manager.read_chunk(file_path, chunk_id)
                        
                        async with aiohttp.ClientSession() as session:
                            form = aiohttp.FormData()
                            form.add_field('file', chunk_data, filename=f'chunk_{chunk_id:06d}')
                            
                            async with session.post(
                                f"{self.relay_url}/transfer/{transfer_id}/chunk/{chunk_id}",
                                data=form
                            ) as resp:
                                if resp.status == 200:
                                    if progress_callback:
                                        progress_callback(chunk_id, total_chunks)
                                    return
                                else:
                                    raise Exception(f"Upload failed: {await resp.text()}")
                    
                    except Exception as e:
                        if attempt == MAX_RETRY_ATTEMPTS - 1:
                            raise
                        await asyncio.sleep(RETRY_DELAY * (attempt + 1))
        
        # Upload all chunks
        tasks = [upload_chunk(i) for i in range(total_chunks)]
        await asyncio.gather(*tasks)
    
    async def _upload_folder_chunks(self, transfer_id: str, manifest: dict, progress_callback=None):
        """Upload chunks for all files in folder"""
        total_chunks = sum(f['totalChunks'] for f in manifest['files'])
        uploaded = 0
        
        for file_info in manifest['files']:
            file_path = file_info['filePath']
            file_chunks = file_info['totalChunks']
            
            # Upload this file's chunks
            for chunk_id in range(file_chunks):
                chunk_data = self.chunk_manager.read_chunk(file_path, chunk_id)
                
                async with aiohttp.ClientSession() as session:
                    form = aiohttp.FormData()
                    form.add_field('file', chunk_data, filename=f'chunk_{chunk_id:06d}')
                    
                    async with session.post(
                        f"{self.relay_url}/transfer/{transfer_id}/chunk/{uploaded}",
                        data=form
                    ) as resp:
                        if resp.status != 200:
                            raise Exception(f"Upload failed: {await resp.text()}")
                
                uploaded += 1
                if progress_callback:
                    progress_callback(uploaded, total_chunks)
    
    async def download_from_relay(self, transfer_id: str, output_path: str, progress_callback=None):
        """Download file/folder from relay server"""
        
        # Get manifest
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.relay_url}/transfer/{transfer_id}/manifest") as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to get manifest: {await resp.text()}")
                manifest = await resp.json()
        
        # Download chunks
        if 'files' in manifest:
            # Folder transfer
            await self._download_folder_chunks(transfer_id, manifest, output_path, progress_callback)
        else:
            # Single file transfer
            await self._download_file_chunks(transfer_id, manifest, output_path, progress_callback)
    
    async def _download_file_chunks(self, transfer_id: str, manifest: dict, output_path: str, progress_callback=None):
        """Download chunks for a single file"""
        total_chunks = manifest['totalChunks']
        
        # Get missing chunks (for resume)
        missing_chunks = self.chunk_manager.get_missing_chunks(output_path, total_chunks)
        
        if not missing_chunks:
            print("✅ File already complete!")
            return
        
        # Download chunks in parallel
        semaphore = asyncio.Semaphore(self.parallel_workers)
        
        async def download_chunk(chunk_id: int):
            async with semaphore:
                for attempt in range(MAX_RETRY_ATTEMPTS):
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(
                                f"{self.relay_url}/transfer/{transfer_id}/chunk/{chunk_id}"
                            ) as resp:
                                if resp.status == 200:
                                    chunk_data = await resp.read()
                                    self.chunk_manager.write_chunk(output_path, chunk_id, chunk_data)
                                    
                                    if progress_callback:
                                        progress_callback(chunk_id, total_chunks)
                                    return
                                else:
                                    raise Exception(f"Download failed: {resp.status}")
                    
                    except Exception as e:
                        if attempt == MAX_RETRY_ATTEMPTS - 1:
                            raise
                        await asyncio.sleep(RETRY_DELAY * (attempt + 1))
        
        # Download missing chunks
        tasks = [download_chunk(i) for i in missing_chunks]
        await asyncio.gather(*tasks)
    
    async def _download_folder_chunks(self, transfer_id: str, manifest: dict, output_path: str, progress_callback=None):
        """Download chunks for all files in folder"""
        base_path = Path(output_path)
        total_chunks = sum(f['totalChunks'] for f in manifest['files'])
        chunk_offset = 0
        
        for file_info in manifest['files']:
            # Create file path
            file_path = base_path / file_info['relativePath']
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download this file's chunks
            for chunk_id in range(file_info['totalChunks']):
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.relay_url}/transfer/{transfer_id}/chunk/{chunk_offset + chunk_id}"
                    ) as resp:
                        if resp.status == 200:
                            chunk_data = await resp.read()
                            self.chunk_manager.write_chunk(str(file_path), chunk_id, chunk_data)
                            
                            if progress_callback:
                                progress_callback(chunk_offset + chunk_id, total_chunks)
                        else:
                            raise Exception(f"Download failed: {resp.status}")
            
            chunk_offset += file_info['totalChunks']
    
    async def download_from_lan(self, server_ip: str, output_path: str, progress_callback=None):
        """Download file/folder via LAN direct"""
        from engine.lan_transfer import LANTransferClient
        
        client = LANTransferClient(server_ip)
        
        # Get manifest
        manifest = await client.get_manifest()
        
        # Download based on type
        if 'files' in manifest:
            # Folder transfer
            await self._download_lan_folder(client, manifest, output_path, progress_callback)
        else:
            # Single file transfer
            await self._download_lan_file(client, manifest, output_path, progress_callback)
    
    async def _download_lan_file(self, client, manifest: dict, output_path: str, progress_callback=None):
        """Download single file via LAN"""
        total_chunks = manifest['totalChunks']
        
        # Download chunks in parallel
        semaphore = asyncio.Semaphore(self.parallel_workers)
        
        async def download_chunk(chunk_id: int):
            async with semaphore:
                chunk_data = await client.download_chunk(chunk_id)
                self.chunk_manager.write_chunk(output_path, chunk_id, chunk_data)
                
                if progress_callback:
                    progress_callback(chunk_id, total_chunks)
        
        tasks = [download_chunk(i) for i in range(total_chunks)]
        await asyncio.gather(*tasks)
    
    async def _download_lan_folder(self, client, manifest: dict, output_path: str, progress_callback=None):
        """Download folder via LAN"""
        base_path = Path(output_path)
        total_chunks = sum(f['totalChunks'] for f in manifest['files'])
        downloaded = 0
        
        for file_index, file_info in enumerate(manifest['files']):
            file_path = base_path / file_info['relativePath']
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            for chunk_id in range(file_info['totalChunks']):
                chunk_data = await client.download_file_chunk(file_index, chunk_id)
                self.chunk_manager.write_chunk(str(file_path), chunk_id, chunk_data)
                
                downloaded += 1
                if progress_callback:
                    progress_callback(downloaded, total_chunks)

if __name__ == "__main__":
    print("Transfer Engine Module")
    print("Use sender_cli.py or receiver_cli.py for actual transfers")
