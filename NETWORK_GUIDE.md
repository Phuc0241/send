# 🌐 Cách Host Lên Mạng

## ✅ Servers đã sẵn sàng host!

Tất cả servers đã được config với `host="0.0.0.0"` - nghĩa là chúng đã lắng nghe trên tất cả network interfaces.

## 🔍 Bước 1: Lấy IP máy bạn

**Cách 1: Dùng file .bat**
- Double-click: `get_ip.bat`
- Ghi lại IP (ví dụ: `192.168.1.7`)

**Cách 2: PowerShell**
```powershell
ipconfig | findstr IPv4
```

**Cách 3: Xem trong Settings**
- Settings → Network & Internet → Wi-Fi → Properties
- Tìm "IPv4 address"

---

## 🚀 Bước 2: Khởi động servers

Chạy 3 servers như bình thường:
1. `start_relay.bat` → Port 8000
2. `start_signaling.bat` → Port 3000
3. `start_web.bat` → Port 5000

---

## 📱 Bước 3: Truy cập từ máy khác

Giả sử IP máy bạn là: **192.168.1.7**

### Từ máy khác (cùng mạng WiFi):

**Mở browser và truy cập:**
```
http://192.168.1.7:5000
```

Bạn sẽ thấy giao diện Send Anywhere!

---

## 🔥 Ví dụ Sử Dụng

### Máy A (192.168.1.7) - Sender:
1. Mở: `http://192.168.1.7:5000`
2. Kéo thả file vào
3. Nhận pair code: `123456`

### Máy B (192.168.1.10) - Receiver:
1. Mở: `http://192.168.1.7:5000` (IP của máy A!)
2. Tab "Receive"
3. Nhập pair code: `123456`
4. Download!

---

## 🔒 Firewall Settings

Nếu máy khác không kết nối được, mở firewall cho các ports:

**PowerShell (Run as Administrator):**
```powershell
# Mở port 3000 (Signaling)
New-NetFirewallRule -DisplayName "Send Anywhere Signaling" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow

# Mở port 5000 (Web UI)
New-NetFirewallRule -DisplayName "Send Anywhere Web UI" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow

# Mở port 8000 (Relay)
New-NetFirewallRule -DisplayName "Send Anywhere Relay" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

---

## 🌍 Truy Cập Từ Internet (Nâng Cao)

Nếu muốn truy cập từ ngoài mạng LAN:

1. **Port Forwarding** trên router:
   - Forward port 5000 → IP máy bạn
   - Forward port 3000 → IP máy bạn
   - Forward port 8000 → IP máy bạn

2. **Lấy Public IP:**
   ```
   https://whatismyipaddress.com
   ```

3. **Truy cập:**
   ```
   http://YOUR_PUBLIC_IP:5000
   ```

⚠️ **Lưu ý bảo mật:** Chỉ mở port khi cần, tắt sau khi dùng xong!

---

## 📊 Kiểm Tra Servers Đang Chạy

```powershell
netstat -an | findstr "3000 5000 8000"
```

Bạn sẽ thấy:
```
TCP    0.0.0.0:3000    LISTENING
TCP    0.0.0.0:5000    LISTENING
TCP    0.0.0.0:8000    LISTENING
```

---

## ✅ Tóm Tắt

1. Chạy `get_ip.bat` → Lấy IP (ví dụ: 192.168.1.7)
2. Chạy 3 servers
3. Truy cập: `http://192.168.1.7:5000` từ bất kỳ máy nào cùng mạng!

Xong! 🎉
