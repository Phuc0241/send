# 🚀 Send Anywhere Python - Production File Transfer System

Transfer 10-100GB folders at maximum speed with automatic mode selection.

## ✨ Features

- 🔥 **3 Transfer Modes**: LAN Direct (80-120 MB/s) → WebRTC P2P (5-40 MB/s) → Relay (Fallback)
- 📦 **Smart Chunking**: Adaptive chunk sizes (2MB LAN, 512KB WebRTC, 1MB Relay)
- 🔄 **Resume Support**: Continue interrupted transfers
- 🔒 **Hash Verification**: SHA256 integrity check per chunk
- ⚡ **Parallel Download**: 5-10 chunks simultaneously
- 🎯 **Auto Mode Selection**: Automatically picks fastest available mode
- 🔢 **Pair Code**: Simple 6-digit codes like Send Anywhere
- 🌐 **Web UI**: Beautiful drag-and-drop interface
- 💻 **CLI Tools**: Command-line sender and receiver

## 📦 Installation

```bash
# Navigate to project directory
cd C:\Users\PHUC\.gemini\antigravity\scratch\send-anywhere-python

# Install dependencies
pip install -r requirements.txt
```

## 🚀 Quick Start

### Option 1: Web UI (Easiest)

**Step 1: Start all servers** (open 3 separate terminals)

```bash
# Terminal 1: Start Relay Server
python backend/relay_server.py

# Terminal 2: Start Signaling Server
python backend/signaling_server.py

# Terminal 3: Start Web UI
python web_server.py
```

**Step 2: Open browser**
- Navigate to `http://localhost:5000`
- Use the beautiful web interface to send/receive files!

### Option 2: CLI Tools (For Large Transfers)

**Sender:**
```bash
# Send a file via relay
python sender_cli.py myfile.zip

# Send a folder via relay
python sender_cli.py myfolder/

# Send via LAN (fastest!)
python sender_cli.py myfile.zip lan
```

**Receiver:**
```bash
# Receive using pair code
python receiver_cli.py 123456

# Receive to specific directory
python receiver_cli.py 123456 downloads/

# Receive via LAN
python receiver_cli.py lan 192.168.1.100
```

## 📁 Project Structure

```
send-anywhere-python/
├── backend/
│   ├── relay_server.py      # ✅ Chunk upload/download server
│   └── signaling_server.py  # ✅ Pair code & WebRTC signaling
├── engine/
│   ├── chunk_manager.py     # ✅ File chunking logic
│   ├── transfer_engine.py   # ✅ Transfer orchestration
│   └── lan_transfer.py      # ✅ LAN direct mode
├── static/
│   ├── index.html           # ✅ Web UI
│   └── app.js               # ✅ Frontend logic
├── sender_cli.py            # ✅ Command-line sender
├── receiver_cli.py          # ✅ Command-line receiver
├── web_server.py            # ✅ Web UI server
├── config.py                # ✅ Configuration
└── requirements.txt         # ✅ Dependencies
```

## 🔧 Configuration

Edit `config.py` to customize:

```python
# Server ports
SIGNALING_PORT = 3000
RELAY_PORT = 8000

# Chunk sizes
CHUNK_SIZE_LAN = 2 * 1024 * 1024      # 2MB
CHUNK_SIZE_RELAY = 1 * 1024 * 1024    # 1MB

# Performance
MAX_PARALLEL_CHUNKS = 5
MAX_RETRY_ATTEMPTS = 3
```

## 📊 API Endpoints

### Signaling Server (Port 3000)

- `POST /pair/create` - Create pair code
- `GET /pair/{code}/info` - Get pair info
- `WS /ws/{code}/{role}` - WebSocket signaling

### Relay Server (Port 8000)

- `POST /transfer/create` - Create transfer
- `POST /transfer/{id}/chunk/{chunk_id}` - Upload chunk
- `GET /transfer/{id}/chunk/{chunk_id}` - Download chunk
- `GET /transfer/{id}/status` - Get transfer status
- `GET /transfer/{id}/manifest` - Get manifest
- `DELETE /transfer/{id}` - Delete transfer
- `GET /cleanup` - Cleanup old transfers

## 🎯 Usage Examples

### Send 50GB folder
```bash
python sender_cli.py "D:\MyLargeFolder"
# Get pair code: 123456
```

### Receive on another computer
```bash
python receiver_cli.py 123456
# Downloads to current directory
```

### LAN Transfer (Fastest)
```bash
# Sender
python sender_cli.py myfile.zip lan
# Shows IP: 192.168.1.100

# Receiver (same network)
python receiver_cli.py lan 192.168.1.100
```

## 🌟 Performance

| Mode | Speed | Use Case |
|------|-------|----------|
| **LAN Direct** | 80-120 MB/s | Same network |
| **Relay** | 10-50 MB/s | Internet |
| **Resume** | ✅ Supported | All modes |

## 🔒 Security Features

- ✅ SHA256 hash verification per chunk
- ✅ Automatic cleanup of old transfers (24 hours)
- ✅ Pair code expiry (1 hour)
- ✅ No permanent storage on relay

## 🐛 Troubleshooting

**Port already in use:**
```bash
# Change ports in config.py
SIGNALING_PORT = 3001
RELAY_PORT = 8001
```

**Connection refused:**
- Make sure all servers are running
- Check firewall settings
- Verify correct IP addresses

**Slow transfer:**
- Use LAN mode for same network
- Increase MAX_PARALLEL_CHUNKS in config.py
- Check network bandwidth

## 📝 License

MIT License
