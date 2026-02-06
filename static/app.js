/**
 * Send Anywhere - Web UI JavaScript
 * Handles file upload, pair code generation, and download
 * Supports both WebRTC (P2P) and Relay (Server-based) transfer
 */

// Production Servers (Render)
const SIGNALING_URL = 'https://send-anywhere-signaling.onrender.com';
const RELAY_URL = 'https://send-anywhere-relay.onrender.com';
const WS_URL = SIGNALING_URL.replace('https', 'wss');

const ICE_SERVERS = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
    ]
};

let selectedFiles = [];
let currentTransferId = null;
let peerConnection = null;
let dataChannel = null;
let signalingSocket = null;
let isP2PConnected = false;

// UI Tabs
function switchTab(tab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    if (tab === 'send') {
        document.getElementById('send-tab-btn').classList.add('active');
        document.getElementById('send-tab').classList.add('active');
    } else {
        document.getElementById('receive-tab-btn').classList.add('active');
        document.getElementById('receive-tab').classList.add('active');
    }
}

// Drag & Drop
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');

if (dropZone) {
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
    dropZone.addEventListener('dragleave', () => { dropZone.classList.remove('drag-over'); });
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        handleFiles(Array.from(e.dataTransfer.files));
    });
}
if (fileInput) {
    fileInput.addEventListener('change', (e) => handleFiles(Array.from(e.target.files)));
}

function handleFiles(files) {
    selectedFiles = files;
    if (files.length === 0) return;
    const totalSize = files.reduce((sum, f) => sum + f.size, 0);
    document.getElementById('fileCount').textContent = files.length;
    document.getElementById('totalSize').textContent = formatSize(totalSize);
    document.getElementById('totalChunks').textContent = Math.ceil(totalSize / (1024 * 1024));
    document.getElementById('fileInfo').classList.add('show');
    startSend();
}

function formatSize(bytes) {
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) { size /= 1024; unitIndex++; }
    return `${size.toFixed(2)} ${units[unitIndex]}`;
}

function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

// ==========================================
// SENDER LOGIC
// ==========================================
async function startSend() {
    if (selectedFiles.length === 0) return;
    try {
        currentTransferId = generateId();
        const manifest = createManifest(selectedFiles);

        // 1. Create Pair Code via HTTP
        const response = await fetch(`${SIGNALING_URL}/pair/create?transfer_id=${currentTransferId}&manifest=${encodeURIComponent(JSON.stringify(manifest))}`, { method: 'POST' });
        if (!response.ok) throw new Error('Failed to create pair code');
        const result = await response.json();

        document.getElementById('pairCode').textContent = result.pair_code;
        document.getElementById('expiryTime').textContent = result.expires_in;
        document.getElementById('pairCodeDisplay').classList.add('show');
        startCountdown(result.expires_in);
        showStatus('sendStatus', '⏳ Waiting for receiver...', 'info');

        // 2. Connect Signaling
        connectSignaling(result.pair_code, 'sender', manifest);

        // 3. Fallback Relay Upload (Background)
        // Delay 3s, if P2P not connected, verify relay logic
        setTimeout(() => {
            if (!isP2PConnected) {
                console.log("P2P Waiting... uploading to Relay just in case.");
                uploadToRelay(currentTransferId, manifest, selectedFiles);
            }
        }, 3000);

    } catch (e) { showStatus('sendStatus', `Error: ${e.message}`, 'error'); }
}

function connectSignaling(code, role, manifest) {
    if (signalingSocket) signalingSocket.close();
    signalingSocket = new WebSocket(`${WS_URL}/ws/${code}/${role}`);

    signalingSocket.onopen = () => console.log(`WS Connected (${role})`);
    signalingSocket.onmessage = (e) => handleSignalingMessage(JSON.parse(e.data), role, manifest);
    signalingSocket.onerror = (e) => console.error("WS Error:", e);
}

async function handleSignalingMessage(msg, role, manifest) {
    switch (msg.type) {
        case 'peer_connected':
            showStatus(role === 'sender' ? 'sendStatus' : 'receiveStatusMsg', '🔗 Peer found! Connecting P2P...', 'info');
            setupWebRTC(role, manifest);
            break;
        case 'offer':
            if (role === 'receiver') {
                await peerConnection.setRemoteDescription(new RTCSessionDescription(msg.offer));
                const answer = await peerConnection.createAnswer();
                await peerConnection.setLocalDescription(answer);
                sendSignal({ type: 'answer', answer: answer });
            }
            break;
        case 'answer':
            if (role === 'sender') await peerConnection.setRemoteDescription(new RTCSessionDescription(msg.answer));
            break;
        case 'candidate':
            if (peerConnection) await peerConnection.addIceCandidate(new RTCIceCandidate(msg.candidate));
            break;
    }
}

function sendSignal(msg) {
    if (signalingSocket?.readyState === WebSocket.OPEN) signalingSocket.send(JSON.stringify(msg));
}

function setupWebRTC(role, manifest) {
    peerConnection = new RTCPeerConnection(ICE_SERVERS);

    peerConnection.onicecandidate = (e) => {
        if (e.candidate) sendSignal({ type: 'candidate', candidate: e.candidate });
    };

    peerConnection.onconnectionstatechange = () => {
        console.log("P2P State:", peerConnection.connectionState);
        if (peerConnection.connectionState === 'connected') {
            isP2PConnected = true;
            const statusId = role === 'sender' ? 'sendStatus' : 'receiveStatusMsg';
            showStatus(statusId, '⚡ P2P Direct Connection! (High Speed)', 'success');
        } else if (peerConnection.connectionState === 'failed') {
            isP2PConnected = false;
        }
    };

    if (role === 'sender') {
        dataChannel = peerConnection.createDataChannel("fileTransfer");
        setupDataChannel(dataChannel, role, manifest);
        peerConnection.createOffer().then(o => peerConnection.setLocalDescription(o)).then(() => sendSignal({ type: 'offer', offer: peerConnection.localDescription }));
    } else {
        peerConnection.ondatachannel = (e) => {
            dataChannel = e.channel;
            setupDataChannel(dataChannel, role, manifest);
        };
    }
}

function setupDataChannel(channel, role, manifest) {
    channel.binaryType = 'arraybuffer';
    channel.onopen = () => {
        console.log("DataChannel OPEN");
        if (role === 'sender') sendFileP2P();
    };
    channel.onmessage = (e) => {
        if (role === 'receiver') handleReceivedData(e.data);
    };
}

// ==========================================
// P2P TRANSFER (SENDER)
// ==========================================
async function sendFileP2P() {
    if (dataChannel?.readyState !== 'open') return;

    showStatus('sendStatus', '🚀 Sending P2P...', 'info');
    document.getElementById('sendProgress').classList.add('show');

    const manifest = createManifest(selectedFiles);
    // 1. Send Manifest
    dataChannel.send(JSON.stringify({ type: 'manifest', data: manifest }));

    const CHUNK_SIZE = 16 * 1024; // 16KB safe chunk
    let totalBytes = 0;
    const totalSize = manifest.type === 'file' ? manifest.size : manifest.totalSize;
    const startTime = Date.now();

    for (const file of selectedFiles) {
        // Send file start marker
        dataChannel.send(JSON.stringify({ type: 'file_start', name: file.name, size: file.size }));

        let offset = 0;
        while (offset < file.size) {
            if (dataChannel.bufferedAmount > 8 * 1024 * 1024) { // 8MB buffer limit
                await new Promise(r => setTimeout(r, 10));
                continue;
            }

            const slice = file.slice(offset, offset + CHUNK_SIZE);
            const buffer = await slice.arrayBuffer();
            dataChannel.send(buffer);

            offset += buffer.byteLength;
            totalBytes += buffer.byteLength;
            updateProgress('sendProgressFill', 'sendSpeed', totalBytes, totalSize, startTime);
        }

        // File end marker (optional but good for sync)
        dataChannel.send(JSON.stringify({ type: 'file_end' }));
    }

    dataChannel.send(JSON.stringify({ type: 'complete' }));
    showStatus('sendStatus', '✅ P2P Sent Successfully!', 'success');
}

// ==========================================
// P2P TRANSFER (RECEIVER)
// ==========================================
let p2pReceivedChunks = [];
let p2pCurrentFileSize = 0;
let p2pCurrentReceived = 0;
let p2pManifest = null;
let p2pCurrentFile = null;

function handleReceivedData(data) {
    if (typeof data === 'string') {
        const msg = JSON.parse(data);
        if (msg.type === 'manifest') {
            p2pManifest = msg.data;
            document.getElementById('receiveProgress').classList.add('show');
        } else if (msg.type === 'file_start') {
            p2pCurrentFile = msg;
            p2pReceivedChunks = [];
            p2pCurrentReceived = 0;
            p2pCurrentFileSize = msg.size;
        } else if (msg.type === 'file_end') {
            saveP2PFile(p2pCurrentFile.name);
        } else if (msg.type === 'complete') {
            showStatus('receiveStatusMsg', '✅ All P2P files received!', 'success');
        }
    } else {
        // Binary Chunk
        p2pReceivedChunks.push(data);
        p2pCurrentReceived += data.byteLength;
        // Simple UI Update
        const totalSize = p2pManifest ? (p2pManifest.type === 'file' ? p2pManifest.size : p2pManifest.totalSize) : p2pCurrentFileSize;
        updateProgress('receiveProgressFill', 'receiveSpeed', p2pCurrentReceived, totalSize, Date.now() - 1000); // Approximate
    }
}

async function saveP2PFile(filename) {
    const blob = new Blob(p2pReceivedChunks);
    p2pReceivedChunks = []; // Clear RAM

    if (window.pywebview) {
        // Desktop Save
        const reader = new FileReader();
        reader.readAsDataURL(blob);
        reader.onloadend = async () => {
            const base64 = reader.result.split(',')[1];
            const savePath = await window.pywebview.api.select_save_file(filename);
            if (savePath.success) {
                await window.pywebview.api.init_file_stream(savePath.path);
                await window.pywebview.api.append_chunk(savePath.path, base64);
                showStatus('receiveStatusMsg', `Saved: ${filename}`, 'success');
            }
        };
    } else {
        // Browser Save
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }
}

// ==========================================
// RECEIVER SETUP
// ==========================================
async function startReceive() {
    const code = document.getElementById('pairCodeInput').value.trim();
    if (code.length !== 6) return showStatus('receiveStatusMsg', 'Invalid Code', 'error');

    try {
        const res = await fetch(`${SIGNALING_URL}/pair/${code}/info`);
        if (!res.ok) throw new Error('Code not found');
        const info = await res.json();
        const manifest = info.manifest;

        displayFileInfo(manifest);
        connectSignaling(code, 'receiver', manifest);

        // Fallback Relay Check
        setTimeout(() => {
            if (!isP2PConnected) {
                console.log("P2P Failed. Downloading from Relay.");
                showStatus('receiveStatusMsg', '⚠️ Using Relay Server (P2P Failed)...', 'info');
                downloadFromRelay(info.transfer_id, manifest);
            }
        }, 3000);

    } catch (e) { showStatus('receiveStatusMsg', e.message, 'error'); }
}

// ==========================================
// HELPERS
// ==========================================
function createManifest(files) {
    if (files.length === 1 && !files[0].webkitRelativePath) {
        return { type: 'file', fileName: files[0].name, size: files[0].size, totalChunks: 1 };
    }
    return {
        type: 'folder',
        totalSize: files.reduce((a, b) => a + b.size, 0),
        totalFiles: files.length,
        files: files.map(f => ({ name: f.name, size: f.size }))
    };
}

function updateProgress(barId, speedId, current, total, startTime) {
    const pct = (current / total) * 100;
    const speed = (current / 1024 / 1024) / (Math.max(1, (Date.now() - startTime) / 1000));
    document.getElementById(barId).style.width = `${pct}%`;
    document.getElementById(barId).textContent = `${pct.toFixed(1)}%`;
    document.getElementById(speedId).textContent = `${speed.toFixed(2)} MB/s`;
}

function displayFileInfo(m) {
    document.getElementById('receiveFileName').textContent = m.type === 'file' ? m.fileName : `${m.totalFiles} files`;
    document.getElementById('receiveFileSize').textContent = formatSize(m.type === 'file' ? m.size : m.totalSize);
    document.getElementById('receiveFileInfo').classList.add('show');
}

function showStatus(id, msg, type) {
    const el = document.getElementById(id);
    if (el) { el.textContent = msg; el.className = `status-message show status-${type}`; }
}

function startCountdown(sec) {
    let t = sec;
    const i = setInterval(() => {
        t--;
        const el = document.getElementById('expiryTime');
        if (el) el.textContent = t;
        if (t <= 0) { clearInterval(i); if (el) el.textContent = 'EXPIRED'; }
    }, 1000);
}

// FALLBACK FUNCTIONS (Simplified Relay Logic)
async function uploadToRelay(tid, m, files) {
    if (isP2PConnected) return;
    try {
        await fetch(`${RELAY_URL}/transfer/create?transfer_id=${tid}&manifest=${encodeURIComponent(JSON.stringify(m))}`, { method: 'POST' });
        let cid = 0;
        for (const f of files) {
            const fd = new FormData(); fd.append('file', f);
            // Uploading whole file as 1 chunk for simplicity in this artifact, real app should chunk
            await fetch(`${RELAY_URL}/transfer/${tid}/chunk/${cid}`, { method: 'POST', body: fd });
            cid++;
        }
    } catch (e) { console.error("Relay Upload Error", e); }
}

async function downloadFromRelay(tid, m) {
    if (isP2PConnected) return;
    document.getElementById('receiveProgress').classList.add('show');
    // Simplified Download: Assume 1 chunk per file for recovery
    // In real app, reuse full download logic
    if (m.type === 'file') {
        const res = await fetch(`${RELAY_URL}/transfer/${tid}/chunk/0`);
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = m.fileName; a.click();
    }
}
