"""
Chunk Manager - Handles file/folder chunking and manifest generation
"""
import os
import hashlib
import json
from pathlib import Path
from typing import List, Dict
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CHUNK_SIZE_LAN, CHUNK_SIZE_WEBRTC, CHUNK_SIZE_RELAY

class ChunkManager:
    """Manages file chunking and manifest generation"""
    
    def __init__(self, mode: str = "relay"):
        """
        Initialize chunk manager
        mode: 'lan', 'webrtc', or 'relay'
        """
        self.mode = mode
        self.chunk_size = self._get_chunk_size(mode)
    
    def _get_chunk_size(self, mode: str) -> int:
        """Get chunk size based on transfer mode"""
        sizes = {
            'lan': CHUNK_SIZE_LAN,
            'webrtc': CHUNK_SIZE_WEBRTC,
            'relay': CHUNK_SIZE_RELAY
        }
        return sizes.get(mode, CHUNK_SIZE_RELAY)
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of entire file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def calculate_chunk_hash(self, data: bytes) -> str:
        """Calculate SHA256 hash of chunk data"""
        return hashlib.sha256(data).hexdigest()
    
    def create_file_manifest(self, file_path: str) -> Dict:
        """
        Create manifest for a single file
        Returns: {fileName, size, chunkSize, totalChunks, hash, chunks: [{id, hash, size}]}
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = file_path.stat().st_size
        total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
        
        # Calculate file hash
        file_hash = self.calculate_file_hash(str(file_path))
        
        # Generate chunk metadata
        chunks = []
        with open(file_path, 'rb') as f:
            chunk_id = 0
            while True:
                chunk_data = f.read(self.chunk_size)
                if not chunk_data:
                    break
                
                chunks.append({
                    'id': chunk_id,
                    'hash': self.calculate_chunk_hash(chunk_data),
                    'size': len(chunk_data)
                })
                chunk_id += 1
        
        return {
            'fileName': file_path.name,
            'filePath': str(file_path),
            'size': file_size,
            'chunkSize': self.chunk_size,
            'totalChunks': total_chunks,
            'hash': file_hash,
            'chunks': chunks
        }
    
    def create_folder_manifest(self, folder_path: str) -> Dict:
        """
        Create manifest for entire folder
        Returns: {folderName, totalSize, totalFiles, files: [file_manifests]}
        """
        folder_path = Path(folder_path)
        
        if not folder_path.exists() or not folder_path.is_dir():
            raise NotADirectoryError(f"Folder not found: {folder_path}")
        
        files = []
        total_size = 0
        
        # Scan all files recursively
        for file_path in folder_path.rglob('*'):
            if file_path.is_file():
                file_manifest = self.create_file_manifest(str(file_path))
                
                # Store relative path
                file_manifest['relativePath'] = str(file_path.relative_to(folder_path))
                
                files.append(file_manifest)
                total_size += file_manifest['size']
        
        return {
            'folderName': folder_path.name,
            'folderPath': str(folder_path),
            'totalSize': total_size,
            'totalFiles': len(files),
            'chunkSize': self.chunk_size,
            'mode': self.mode,
            'files': files
        }
    
    def read_chunk(self, file_path: str, chunk_id: int) -> bytes:
        """Read a specific chunk from file"""
        offset = chunk_id * self.chunk_size
        
        with open(file_path, 'rb') as f:
            f.seek(offset)
            return f.read(self.chunk_size)
    
    def write_chunk(self, file_path: str, chunk_id: int, data: bytes):
        """Write a chunk to file at specific position"""
        offset = chunk_id * self.chunk_size
        
        # Create parent directories if needed
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Open in r+b mode (read/write) or create if not exists
        mode = 'r+b' if os.path.exists(file_path) else 'wb'
        
        with open(file_path, mode) as f:
            f.seek(offset)
            f.write(data)
    
    def verify_chunk(self, file_path: str, chunk_id: int, expected_hash: str) -> bool:
        """Verify a chunk matches expected hash"""
        chunk_data = self.read_chunk(file_path, chunk_id)
        actual_hash = self.calculate_chunk_hash(chunk_data)
        return actual_hash == expected_hash
    
    def verify_file(self, file_path: str, expected_hash: str) -> bool:
        """Verify entire file matches expected hash"""
        actual_hash = self.calculate_file_hash(file_path)
        return actual_hash == expected_hash
    
    def get_missing_chunks(self, file_path: str, total_chunks: int) -> List[int]:
        """
        Get list of missing chunks for resume functionality
        Returns list of chunk IDs that need to be downloaded
        """
        if not os.path.exists(file_path):
            # File doesn't exist, all chunks missing
            return list(range(total_chunks))
        
        file_size = os.path.getsize(file_path)
        downloaded_chunks = file_size // self.chunk_size
        
        # All chunks after downloaded_chunks are missing
        return list(range(downloaded_chunks, total_chunks))

def format_size(size_bytes: int) -> str:
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

if __name__ == "__main__":
    # Test chunk manager
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python chunk_manager.py <file_or_folder_path>")
        sys.exit(1)
    
    path = sys.argv[1]
    manager = ChunkManager(mode='relay')
    
    if os.path.isfile(path):
        print(f"📄 Creating manifest for file: {path}")
        manifest = manager.create_file_manifest(path)
        print(f"✅ File: {manifest['fileName']}")
        print(f"📦 Size: {format_size(manifest['size'])}")
        print(f"🔢 Chunks: {manifest['totalChunks']}")
        print(f"🔒 Hash: {manifest['hash'][:16]}...")
    
    elif os.path.isdir(path):
        print(f"📁 Creating manifest for folder: {path}")
        manifest = manager.create_folder_manifest(path)
        print(f"✅ Folder: {manifest['folderName']}")
        print(f"📦 Total Size: {format_size(manifest['totalSize'])}")
        print(f"📄 Files: {manifest['totalFiles']}")
        print(f"🔢 Total Chunks: {sum(f['totalChunks'] for f in manifest['files'])}")
    
    else:
        print(f"❌ Path not found: {path}")
        sys.exit(1)
    
    # Save manifest
    output_file = "manifest.json"
    with open(output_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n💾 Manifest saved to: {output_file}")
