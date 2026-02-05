# Send Anywhere - Render.com Deployment

## Quick Deploy Guide

### Step 1: Push to GitHub

```bash
cd C:\Users\PHUC\.gemini\antigravity\scratch\send-anywhere-python

# Initialize git
git init
git add .
git commit -m "Ready for Render deployment"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/send-anywhere-python.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy Relay Server

1. Go to https://render.com → Sign up/Login
2. Click **"New +"** → **"Web Service"**
3. Connect GitHub → Select your repository
4. Configure:
   - **Name**: `send-anywhere-relay`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python relay_server_render.py`
   - **Instance Type**: `Free`
5. Click **"Create Web Service"**
6. **Copy the URL** (e.g., `https://send-anywhere-relay.onrender.com`)

### Step 3: Deploy Signaling Server

1. Click **"New +"** → **"Web Service"**
2. Select same repository
3. Configure:
   - **Name**: `send-anywhere-signaling`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python signaling_server_render.py`
   - **Instance Type**: `Free`
4. Click **"Create Web Service"**
5. **Copy the URL** (e.g., `https://send-anywhere-signaling.onrender.com`)

### Step 4: Update Desktop App

Edit `static/app.js` - find these lines and replace:

```javascript
// OLD (local servers):
const CURRENT_HOST = window.location.hostname;
const SIGNALING_URL = `http://${CURRENT_HOST}:3000`;
const RELAY_URL = `http://${CURRENT_HOST}:8000`;

// NEW (Render servers):
const SIGNALING_URL = 'https://send-anywhere-signaling.onrender.com';
const RELAY_URL = 'https://send-anywhere-relay.onrender.com';
```

**Important**: Change `http://` to `https://` and `ws://` to `wss://` for WebSocket!

### Step 5: Rebuild App

```bash
build.bat
```

### Step 6: Test!

1. Open app on Computer A → Send file → Get code
2. Open app on Computer B → Enter code → Download
3. Both use same Render servers! 🎉

## Keep Servers Awake (Optional)

Free tier sleeps after 15 min. To keep awake:

1. Go to https://uptimerobot.com (free)
2. Add monitors for both URLs
3. Ping every 5 minutes
4. Servers stay awake 24/7!

## Troubleshooting

**"Can't connect"**: Wait 30s (server waking up)
**CORS error**: Check if CORS is enabled in server files
**WebSocket error**: Make sure using `wss://` not `ws://`
