"""
Configuration settings for Send Anywhere Python
"""
import os

# Server Configuration
SIGNALING_HOST = "0.0.0.0"
SIGNALING_PORT = 3000

RELAY_HOST = "0.0.0.0"
RELAY_PORT = 8000

# Storage Configuration
UPLOAD_DIR = "uploads"
TEMP_DIR = "temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Transfer Configuration
CHUNK_SIZE_LAN = 2 * 1024 * 1024      # 2MB for LAN
CHUNK_SIZE_WEBRTC = 512 * 1024        # 512KB for WebRTC
CHUNK_SIZE_RELAY = 1 * 1024 * 1024    # 1MB for Relay

# Performance Configuration
MAX_PARALLEL_CHUNKS = 5               # Download 5 chunks simultaneously
MIN_PARALLEL_CHUNKS = 1
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 2                       # seconds

# Cleanup Configuration
CLEANUP_AFTER_HOURS = 24              # Auto-delete transfers after 24 hours

# Pair Code Configuration
PAIR_CODE_LENGTH = 6
PAIR_CODE_EXPIRY = 3600               # 1 hour in seconds

# Network Configuration
LAN_DISCOVERY_PORT = 9000
CONNECTION_TIMEOUT = 30               # seconds
CHUNK_TIMEOUT = 60                    # seconds per chunk
