/**
 * Send Anywhere - Web UI JavaScript
 * Handles file upload, pair code generation, and download
 * Supports both WebRTC (P2P) and Relay (Server-based) transfer
 */

// Connection Config
const SIGNALING_URL = 'https://send-anywhere-signaling.onrender.com';
const RELAY_URL = 'https://send-anywhere-relay.onrender.com';
const WS_URL = SIGNALING_URL.replace('https', 'wss');
const ICE_SERVERS = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

// State
let selectedFiles = [];
let currentTransferId = null;
let peerConnection = null;
let dataChannel = null;
let signalingSocket = null;
let isP2PConnected = false;
let p2pZip = null; // For Web Folder Receive
let p2pDesktopTargetFolder = null; // For Desktop Folder Receive

// UI Helpers
const $ = (id) => document.getElementById(id);
const show = (id) => $(id)?.classList.add('show');
const hide = (id) => $(id)?.classList.remove('show');

function switchTab(tab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    if (tab === 'send') {
        $('send-tab').classList.add('active');
        document.querySelector('button[onclick="switchTab(\'send\')"]').classList.add('active');
    } else {
        $('receive-tab').classList.add('active');
        document.querySelector('button[onclick="switchTab(\'receive\')"]').classList.add('active');
    }
}

// Drag & Drop
const dropZone = $('dropZone');
if (dropZone) {
    dropZone.addEventListener('click', () => $('fileInput').click());
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault(); dropZone.classList.remove('drag-over');
        handleFiles(Array.from(e.dataTransfer.files));
    });
}
$('fileInput').addEventListener('change', (e) => handleFiles(Array.from(e.target.files)));

function handleFiles(files) {
    selectedFiles = files;
    if (files.length === 0) return;
    const totalSize = files.reduce((sum, f) => sum + f.size, 0);
    $('fileCount').textContent = files.length;
    $('totalSize').textContent = formatSize(totalSize);
    $('totalChunks').textContent = Math.ceil(totalSize / (1024 * 1024));
    show('fileInfo');
    startSend();
}

function formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return parseFloat((bytes / Math.pow(1024, i)).toFixed(2)) + ' ' + units[i];
}

// ==========================================
// SENDER
// ==========================================
async function startSend() {
    if (selectedFiles.length === 0) return;
    try {
        currentTransferId = Date.now().toString(36);
        const manifest = createManifest(selectedFiles);

        const res = await fetch(`${SIGNALING_URL}/pair/create?transfer_id=${currentTransferId}&manifest=${encodeURIComponent(JSON.stringify(manifest))}`, { method: 'POST' });
        if (!res.ok) throw new Error('Create Pair Code Failed');
        const data = await res.json();

        $('pairCode').textContent = data.pair_code;
        $('expiryTime').textContent = data.expires_in;
        show('pairCodeDisplay');
        startCountdown(data.expires_in);

        showStatus('sendStatus', '⏳ Waiting for receiver...', 'info');
        connectSignaling(data.pair_code, 'sender', manifest);

        // Fallback
        setTimeout(() => {
            if (!isP2PConnected) {
                console.log("P2P Slow/Failed -> Uploading to Relay...");
                uploadToRelay(currentTransferId, manifest, selectedFiles);
            }
        }, 4000);

    } catch (e) { showStatus('sendStatus', `Error: ${e.message}`, 'error'); }
}

function createManifest(files) {
    // Detect folder logic
    let type = 'file';
    let folderName = 'download';

    // Check if multiple files or folder structure
    if (files.length > 1 || (files[0].webkitRelativePath && files[0].webkitRelativePath.includes('/'))) {
        type = 'folder';
        if (files[0].webkitRelativePath) {
            folderName = files[0].webkitRelativePath.split('/')[0];
        }
    } else {
        folderName = files[0].name; // Single file name
    }

    return {
        type: type,
        folderName: folderName,
        totalSize: files.reduce((a, b) => a + b.size, 0),
        totalFiles: files.length,
        files: files.map(f => ({
            name: f.name,
            path: f.webkitRelativePath || f.name,
            size: f.size
        }))
    };
}

// ==========================================
// P2P SENDER logic
// ==========================================
async function sendFileP2P() {
    if (dataChannel?.readyState !== 'open') return;
    showStatus('sendStatus', '🚀 Sending P2P...', 'info');
    show('sendProgress');

    const manifest = createManifest(selectedFiles);
    dataChannel.send(JSON.stringify({ type: 'manifest', data: manifest }));

    const CHUNK_SIZE = 16 * 1024; // 16KB for safe WebRTC
    let totalSent = 0;
    const totalSize = manifest.totalSize;
    const startTime = Date.now();

    for (const file of selectedFiles) {
        // Send file header
        dataChannel.send(JSON.stringify({
            type: 'file_start',
            name: file.name,
            path: file.webkitRelativePath || file.name,
            size: file.size
        }));

        let offset = 0;
        while (offset < file.size) {
            // Flow control
            if (dataChannel.bufferedAmount > 8 * 1024 * 1024) {
                await new Promise(r => setTimeout(r, 10)); continue;
            }

            const slice = file.slice(offset, offset + CHUNK_SIZE);
            const buffer = await slice.arrayBuffer();
            dataChannel.send(buffer);

            offset += buffer.byteLength;
            totalSent += buffer.byteLength;
            updateProgress('sendProgressFill', 'sendSpeed', totalSent, totalSize, startTime);
        }
        dataChannel.send(JSON.stringify({ type: 'file_end' }));
    }

    dataChannel.send(JSON.stringify({ type: 'complete' }));
    showStatus('sendStatus', '✅ P2P Transfer Complete!', 'success');
}

// ==========================================
// RECEIVER
// ==========================================
let p2pReceivedChunks = [];
let p2pCurrentReceived = 0;
let p2pManifest = null;
let p2pCurrentFile = null;

async function startReceive() {
    const code = $('pairCodeInput').value.trim();
    if (code.length !== 6) return showStatus('receiveStatusMsg', 'Invalid Code', 'error');

    try {
        const res = await fetch(`${SIGNALING_URL}/pair/${code}/info`);
        if (!res.ok) throw new Error('Code not found');
        const info = await res.json();

        // Setup UI
        const m = info.manifest;
        $('receiveFileName').textContent = m.folderName;
        $('receiveFileSize').textContent = formatSize(m.totalSize);
        show('receiveFileInfo');

        // Connect
        connectSignaling(code, 'receiver', m);

        // Fallback
        setTimeout(() => {
            if (!isP2PConnected) {
                console.log("P2P Failed -> Using Relay");
                showStatus('receiveStatusMsg', '⚠️ Using Relay Server...', 'info');
                downloadFromRelay(info.transfer_id, m);
            }
        }, 4000);

    } catch (e) { showStatus('receiveStatusMsg', e.message, 'error'); }
}

// Handle Incoming P2P Data
async function handleReceivedData(data) {
    // 1. JSON Message
    if (typeof data === 'string') {
        const msg = JSON.parse(data);
        if (msg.type === 'manifest') {
            p2pManifest = msg.data;
            show('receiveProgress');

            // Initialize Storage Strategy
            if (window.pywebview) {
                // Desktop: Ask for folder ONCE
                if (p2pManifest.type === 'folder' || p2pManifest.totalFiles > 1) {
                    const res = await window.pywebview.api.select_folder();
                    if (res.success) p2pDesktopTargetFolder = res.path;
                    else return alert("Transfer Cancelled: No folder selected");
                }
            } else {
                // Web: Init Zip
                if (p2pManifest.type === 'folder' || p2pManifest.totalFiles > 1) {
                    p2pZip = new JSZip();
                }
            }
        }
        else if (msg.type === 'file_start') {
            p2pCurrentFile = msg;
            p2pReceivedChunks = [];
        }
        else if (msg.type === 'file_end') {
            await saveP2PFile();
        }
        else if (msg.type === 'complete') {
            finishP2PReceive();
        }
    }
    // 2. Binary Chunk
    else {
        p2pReceivedChunks.push(data);
        p2pCurrentReceived += data.byteLength;
        updateProgress('receiveProgressFill', 'receiveSpeed', p2pCurrentReceived, p2pManifest?.totalSize || 0, Date.now() - 1000);
    }
}

async function saveP2PFile() {
    const blob = new Blob(p2pReceivedChunks);
    p2pReceivedChunks = []; // Clean RAM

    // Case 1: Desktop App (Direct Write)
    if (window.pywebview) {
        const reader = new FileReader();
        reader.readAsDataURL(blob);
        reader.onloadend = async () => {
            const base64 = reader.result.split(',')[1];
            let savePath = '';

            if (p2pDesktopTargetFolder) {
                // Folder mode: Construct path using relative path
                // Remove root folder name from relative path to avoid duplication if needed
                // Assuming p2pCurrentFile.path is like "Folder/Sub/File.txt"
                // And user selected "C:/Desc"
                // We want "C:/Desc/Folder/Sub/File.txt"
                savePath = p2pDesktopTargetFolder + '\\' + p2pCurrentFile.path.replace(/\//g, '\\');
            } else {
                // Single file mode: Ask save
                const res = await window.pywebview.api.select_save_file(p2pCurrentFile.name);
                if (res.success) savePath = res.path;
            }

            if (savePath) {
                await window.pywebview.api.init_file_stream(savePath);
                await window.pywebview.api.append_chunk(savePath, base64);
            }
        };
    }
    // Case 2: Web Browser (Zip or Download)
    else {
        if (p2pZip) {
            // Folder mode: Add to Zip
            p2pZip.file(p2pCurrentFile.path, blob);
        } else {
            // Single file mode: Download immediately
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = p2pCurrentFile.name; a.click();
        }
    }
}

async function finishP2PReceive() {
    showStatus('receiveStatusMsg', '✅ All files received!', 'success');

    // If Web + Folder -> Generate Zip
    if (!window.pywebview && p2pZip) {
        showStatus('receiveStatusMsg', '📦 Zipping files...', 'info');
        const content = await p2pZip.generateAsync({ type: "blob" });
        const url = URL.createObjectURL(content);
        const a = document.createElement('a');
        a.href = url;
        a.download = (p2pManifest.folderName || 'download') + ".zip";
        a.click();
        showStatus('receiveStatusMsg', '✅ Zip Downloaded!', 'success');
    }

    if (window.pywebview && p2pDesktopTargetFolder) {
        alert(`✅ Folder Download Complete!\nSaved to: ${p2pDesktopTargetFolder}`);
    }
}

// ==========================================
// WEBRTC SIGNALING
// ==========================================
function connectSignaling(code, role, manifest) {
    if (signalingSocket) signalingSocket.close();
    signalingSocket = new WebSocket(`${WS_URL}/ws/${code}/${role}`);
    signalingSocket.onopen = () => console.log('WS Connected');
    signalingSocket.onmessage = (e) => handleSigMsg(JSON.parse(e.data), role, manifest);
}

async function handleSigMsg(msg, role, manifest) {
    if (msg.type === 'peer_connected') {
        showStatus(role === 'sender' ? 'sendStatus' : 'receiveStatusMsg', '🔗 Peer Connected!', 'info');
        setupWebRTC(role, manifest);
    } else if (msg.type === 'offer' && role === 'receiver') {
        await peerConnection.setRemoteDescription(msg.offer);
        const ans = await peerConnection.createAnswer();
        await peerConnection.setLocalDescription(ans);
        sendSig({ type: 'answer', answer: ans });
    } else if (msg.type === 'answer' && role === 'sender') {
        await peerConnection.setRemoteDescription(msg.answer);
    } else if (msg.type === 'candidate') {
        if (peerConnection) peerConnection.addIceCandidate(msg.candidate);
    }
}

function sendSig(msg) { signalingSocket?.send(JSON.stringify(msg)); }

function setupWebRTC(role, manifest) {
    peerConnection = new RTCPeerConnection(ICE_SERVERS);
    peerConnection.onicecandidate = (e) => e.candidate && sendSig({ type: 'candidate', candidate: e.candidate });
    peerConnection.onconnectionstatechange = () => {
        if (peerConnection.connectionState === 'connected') {
            isP2PConnected = true;
            showStatus(role === 'sender' ? 'sendStatus' : 'receiveStatusMsg', '⚡ P2P Direct!', 'success');
        } else if (peerConnection.connectionState === 'failed') isP2PConnected = false;
    };

    if (role === 'sender') {
        dataChannel = peerConnection.createDataChannel("fileTransfer");
        setupDataChannel(dataChannel, role, manifest);
        peerConnection.createOffer().then(o => peerConnection.setLocalDescription(o)).then(() => sendSig({ type: 'offer', offer: peerConnection.localDescription }));
    } else {
        peerConnection.ondatachannel = (e) => {
            dataChannel = e.channel;
            setupDataChannel(dataChannel, role, manifest);
        };
    }
}

function setupDataChannel(ch, role, m) {
    ch.binaryType = 'arraybuffer';
    ch.onopen = () => role === 'sender' && sendFileP2P();
    ch.onmessage = (e) => role === 'receiver' && handleReceivedData(e.data);
}

// ==========================================
// UTILS
// ==========================================
function updateProgress(bar, spd, curr, tot, start) {
    const pct = (curr / tot) * 100;
    const s = (curr / 1024 / 1024) / Math.max(1, (Date.now() - start) / 1000);
    $(bar).style.width = pct + '%';
    $(bar).textContent = pct.toFixed(1) + '%';
    $(spd).textContent = s.toFixed(2) + ' MB/s';
}

function showStatus(id, msg, type) {
    if ($(id)) { $(id).textContent = msg; $(id).className = `status-message show status-${type}`; }
}

function startCountdown(sec) {
    let t = sec;
    const i = setInterval(() => { if ($('expiryTime')) $('expiryTime').textContent = --t; if (t <= 0) clearInterval(i); }, 1000);
}

// Simple Relay Upload (Fallback)
async function uploadToRelay(tid, m, files) {
    if (isP2PConnected) return;
    try {
        await fetch(`${RELAY_URL}/transfer/create?transfer_id=${tid}&manifest=${encodeURIComponent(JSON.stringify(m))}`, { method: 'POST' });
        let i = 0; for (const f of files) {
            const fd = new FormData(); fd.append('file', f);
            await fetch(`${RELAY_URL}/transfer/${tid}/chunk/${i++}`, { method: 'POST', body: fd });
        }
    } catch (e) { }
}

async function downloadFromRelay(tid, m) {
    if (isP2PConnected) return;
    // Simple Relay Download Fallback
    showStatus('receiveStatusMsg', 'Running Relay Download...', 'info');
    // Using basic browser download for fail-safe
    if (m.type === 'file') {
        window.open(`${RELAY_URL}/transfer/${tid}/chunk/0`);
    } else {
        alert("Relay Folder Download not fully implemented in this lightweight version. Use P2P for best results.");
    }
}
