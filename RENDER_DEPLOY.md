# Deploying to Render.com

This guide shows how to deploy the Relay and Signaling servers to Render.com so multiple users can use the same backend.

## Prerequisites

1. GitHub account
2. Render.com account (free, no credit card needed)

## Step 1: Push Code to GitHub

```bash
cd C:\Users\PHUC\.gemini\antigravity\scratch\send-anywhere-python

# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit"

# Create a new repository on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/send-anywhere-python.git
git push -u origin main
```

## Step 2: Deploy Relay Server to Render

1. Go to https://render.com and sign up/login
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `send-anywhere-relay`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.relay_server:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
5. Click **"Create Web Service"**
6. Wait for deployment (~2-3 minutes)
7. Copy the URL (e.g., `https://send-anywhere-relay.onrender.com`)

## Step 3: Deploy Signaling Server to Render

1. Click **"New +"** → **"Web Service"** again
2. Select same GitHub repository
3. Configure:
   - **Name**: `send-anywhere-signaling`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.signaling_server:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
4. Click **"Create Web Service"**
5. Copy the URL (e.g., `https://send-anywhere-signaling.onrender.com`)

## Step 4: Update Desktop App Configuration

Edit `config.py` to point to your Render servers:

```python
# Server URLs (update these with your Render URLs)
RELAY_URL = "https://send-anywhere-relay.onrender.com"
SIGNALING_URL = "https://send-anywhere-signaling.onrender.com"
```

Then rebuild the app:

```bash
build.bat
```

## Step 5: Update Frontend URLs

Edit `static/app.js` to use your Render servers:

```javascript
// Replace these lines:
const RELAY_URL = `http://${CURRENT_HOST}:8000`;
const SIGNALING_URL = `http://${CURRENT_HOST}:3000`;

// With:
const RELAY_URL = 'https://send-anywhere-relay.onrender.com';
const SIGNALING_URL = 'wss://send-anywhere-signaling.onrender.com';
```

## Important Notes

### Free Tier Limitations

- **Sleep after 15 minutes**: Render free tier apps sleep after 15 minutes of inactivity
- **Wake-up time**: ~30 seconds on first request
- **Solution**: Use [UptimeRobot](https://uptimerobot.com) to ping your servers every 5 minutes (keeps them awake)

### HTTPS/WSS

- Render provides free HTTPS automatically
- WebSocket connections use `wss://` instead of `ws://`

### CORS Configuration

You may need to add CORS headers to allow desktop app to connect. Add to both servers:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Testing

1. Open app on Computer A → Send file → Get pair code
2. Open app on Computer B → Enter pair code → Download file
3. Both computers now use the same Render servers! 🎉

## Troubleshooting

### App won't connect
- Check if Render services are running (not sleeping)
- Verify URLs in `config.py` and `app.js`
- Check browser console for CORS errors

### Slow first connection
- Normal for free tier (app is waking up)
- Use UptimeRobot to keep apps awake

### Files not transferring
- Check Render logs for errors
- Verify both Relay and Signaling servers are deployed
