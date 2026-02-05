# Quick Start Guide

## 🚀 Cách Chạy Nhanh Nhất

### Bước 1: Cài đặt dependencies
```bash
cd C:\Users\PHUC\.gemini\antigravity\scratch\send-anywhere-python
pip install -r requirements.txt
```

### Bước 2: Khởi động servers (3 terminals)

**Terminal 1 - Relay Server:**
```bash
python backend\relay_server.py
```

**Terminal 2 - Signaling Server:**
```bash
python backend\signaling_server.py
```

**Terminal 3 - Web UI:**
```bash
python web_server.py
```

### Bước 3: Sử dụng

**Web UI:**
- Mở browser: `http://localhost:5000`
- Kéo thả file vào
- Nhận pair code và share

**CLI (Gửi file lớn):**
```bash
# Gửi
python sender_cli.py "D:\MyFolder"

# Nhận
python receiver_cli.py 123456
```

## 🎯 Test Nhanh

```bash
# Tạo file test 100MB
python -c "with open('test.bin', 'wb') as f: f.write(b'0' * 100*1024*1024)"

# Gửi
python sender_cli.py test.bin

# Nhận (terminal khác)
python receiver_cli.py <pair_code>
```

Xong! 🎉
