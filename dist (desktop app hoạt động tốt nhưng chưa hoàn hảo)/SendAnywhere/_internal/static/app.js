/**
 * Send Anywhere - Web UI JavaScript
 * Handles file upload, pair code generation, and download
 */

// Use current hostname instead of localhost for network access
const CURRENT_HOST = window.location.hostname;
const SIGNALING_URL = `http://${CURRENT_HOST}:3000`;
const RELAY_URL = `http://${CURRENT_HOST}:8000`;

let selectedFiles = [];
let currentTransferId = null;

// Tab switching
function switchTab(tab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    if (tab === 'send') {
        document.querySelectorAll('.tab')[0].classList.add('active');
        document.getElementById('send-tab').classList.add('active');
    } else {
        document.querySelectorAll('.tab')[1].classList.add('active');
        document.getElementById('receive-tab').classList.add('active');
    }
}

// Drop zone handling
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');

dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');

    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
});

fileInput.addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    handleFiles(files);
});

// Handle selected files
function handleFiles(files) {
    selectedFiles = files;

    if (files.length === 0) return;

    // Calculate total size
    const totalSize = files.reduce((sum, file) => sum + file.size, 0);
    const chunkSize = 1024 * 1024; // 1MB
    const totalChunks = Math.ceil(totalSize / chunkSize);

    // Display file info
    document.getElementById('fileCount').textContent = files.length;
    document.getElementById('totalSize').textContent = formatSize(totalSize);
    document.getElementById('totalChunks').textContent = totalChunks;
    document.getElementById('fileInfo').classList.add('show');

    // Auto-start upload
    startSend();
}

// Format bytes to human readable
function formatSize(bytes) {
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }

    return `${size.toFixed(2)} ${units[unitIndex]}`;
}

// Start sending files
async function startSend() {
    if (selectedFiles.length === 0) {
        showStatus('sendStatus', 'Please select files first', 'error');
        return;
    }

    try {
        // Generate transfer ID
        currentTransferId = generateId();

        // Create manifest
        const manifest = createManifest(selectedFiles);

        // Create pair code
        const response = await fetch(`${SIGNALING_URL}/pair/create?transfer_id=${currentTransferId}&manifest=${encodeURIComponent(JSON.stringify(manifest))}`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('Failed to create pair code');
        }

        const result = await response.json();

        // Display pair code
        document.getElementById('pairCode').textContent = result.pair_code;
        document.getElementById('expiryTime').textContent = result.expires_in;
        document.getElementById('pairCodeDisplay').classList.add('show');

        // Start countdown
        startCountdown(result.expires_in);

        // Upload to relay
        await uploadToRelay(currentTransferId, manifest, selectedFiles);

    } catch (error) {
        showStatus('sendStatus', `Error: ${error.message}`, 'error');
    }
}

// Create manifest from selected files
function createManifest(files) {
    if (files.length === 0) return null;

    // Check if single file or folder
    const isSingleFile = files.length === 1 && !files[0].webkitRelativePath;

    if (isSingleFile) {
        // Single file
        const file = files[0];
        const chunkSize = 1024 * 1024; // 1MB chunks
        const totalChunks = Math.ceil(file.size / chunkSize);

        return {
            type: 'file',
            fileName: file.name,
            size: file.size,
            chunkSize: chunkSize,
            totalChunks: totalChunks
        };
    } else {
        // Folder or multiple files
        const chunkSize = 1024 * 1024; // 1MB chunks
        let totalSize = 0;
        const fileList = [];

        // Extract folder name from first file's path
        let folderName = 'download';
        if (files[0].webkitRelativePath) {
            const pathParts = files[0].webkitRelativePath.split('/');
            folderName = pathParts[0]; // First part is folder name
        }

        for (const file of files) {
            const totalChunks = Math.ceil(file.size / chunkSize);
            totalSize += file.size;

            // Preserve full path structure
            let filePath = file.name;
            if (file.webkitRelativePath) {
                // Remove root folder name to get relative path inside folder
                const pathParts = file.webkitRelativePath.split('/');
                pathParts.shift(); // Remove first part (root folder name)
                filePath = pathParts.join('/'); // Rejoin with subdirectories
            }

            fileList.push({
                fileName: file.name,
                filePath: filePath, // Full path with subdirectories
                size: file.size,
                totalChunks: totalChunks
            });
        }

        return {
            type: 'folder',
            folderName: folderName,
            totalSize: totalSize,
            totalFiles: files.length,
            chunkSize: chunkSize,
            files: fileList
        };
    }
}

// Upload to relay server
async function uploadToRelay(transferId, manifest, files) {
    // Create transfer
    const createResponse = await fetch(`${RELAY_URL}/transfer/create?transfer_id=${transferId}&manifest=${encodeURIComponent(JSON.stringify(manifest))}`, {
        method: 'POST'
    });

    if (!createResponse.ok) {
        throw new Error('Failed to create transfer on relay');
    }

    // Show progress
    document.getElementById('sendProgress').classList.add('show');

    // Upload chunks
    const chunkSize = manifest.chunkSize;
    let chunkId = 0;
    let uploadedBytes = 0;
    const totalSize = manifest.type === 'file' ? manifest.size : manifest.totalSize;
    const startTime = Date.now();

    for (const file of files) {
        const fileChunks = Math.ceil(file.size / chunkSize);

        for (let i = 0; i < fileChunks; i++) {
            const start = i * chunkSize;
            const end = Math.min(start + chunkSize, file.size);
            const chunk = file.slice(start, end);

            // Upload chunk
            const formData = new FormData();
            formData.append('file', chunk);

            const uploadResponse = await fetch(`${RELAY_URL}/transfer/${transferId}/chunk/${chunkId}`, {
                method: 'POST',
                body: formData
            });

            if (!uploadResponse.ok) {
                throw new Error(`Failed to upload chunk ${chunkId}`);
            }

            // Update progress
            uploadedBytes += chunk.size;
            const progress = (uploadedBytes / totalSize) * 100;
            const elapsed = (Date.now() - startTime) / 1000;
            const speed = uploadedBytes / elapsed / 1024 / 1024; // MB/s

            document.getElementById('sendProgressFill').style.width = `${progress}%`;
            document.getElementById('sendProgressFill').textContent = `${progress.toFixed(1)}%`;
            document.getElementById('sendSpeed').textContent = `${speed.toFixed(2)} MB/s`;

            chunkId++;
        }
    }

    showStatus('sendStatus', '✅ Upload complete! Receiver can now download.', 'success');
}

// Start expiry countdown
function startCountdown(seconds) {
    let remaining = seconds;
    const interval = setInterval(() => {
        remaining--;
        document.getElementById('expiryTime').textContent = remaining;

        if (remaining <= 0) {
            clearInterval(interval);
            document.getElementById('expiryTime').textContent = 'EXPIRED';
        }
    }, 1000);
}

// Start receiving
async function startReceive() {
    const pairCode = document.getElementById('pairCodeInput').value.trim();

    if (!pairCode || pairCode.length !== 6) {
        showStatus('receiveStatusMsg', 'Please enter a valid 6-digit pair code', 'error');
        return;
    }

    try {
        // Get pair info
        const response = await fetch(`${SIGNALING_URL}/pair/${pairCode}/info`);

        if (!response.ok) {
            throw new Error('Invalid or expired pair code');
        }

        const pairInfo = await response.json();
        const manifest = pairInfo.manifest;

        // Display file info
        if (manifest.type === 'file') {
            document.getElementById('receiveFileName').textContent = manifest.fileName;
            document.getElementById('receiveFileSize').textContent = formatSize(manifest.size);
            document.getElementById('receiveChunks').textContent = manifest.totalChunks;
        } else {
            document.getElementById('receiveFileName').textContent = `${manifest.totalFiles} files`;
            document.getElementById('receiveFileSize').textContent = formatSize(manifest.totalSize);
            document.getElementById('receiveChunks').textContent = manifest.files.reduce((sum, f) => sum + f.totalChunks, 0);
        }

        document.getElementById('receiveFileInfo').classList.add('show');

        // Download from relay
        await downloadFromRelay(pairInfo.transfer_id, manifest);

    } catch (error) {
        showStatus('receiveStatusMsg', `Error: ${error.message}`, 'error');
    }
}

// Download from relay
async function downloadFromRelay(transferId, manifest) {
    document.getElementById('receiveProgress').classList.add('show');

    try {
        if (manifest.type === 'file') {
            // Single file download
            await downloadSingleFile(transferId, manifest);
        } else {
            // Folder download - download each file and create ZIP
            await downloadFolder(transferId, manifest);
        }
    } catch (error) {
        showStatus('receiveStatusMsg', `❌ Error: ${error.message}`, 'error');
        throw error;
    }
}

// Download single file
// Global abort controller for cancellation
let downloadAbortController = null;

// Cancel download
function cancelDownload() {
    if (downloadAbortController) {
        downloadAbortController.abort();
        downloadAbortController = null;
        showStatus('receiveStatusMsg', '🛑 Download cancelled by user', 'error');
        document.getElementById('receiveProgress').classList.remove('show');
        resetReceiveUI();
    }
}

function resetReceiveUI() {
    document.getElementById('receiveProgressFill').style.width = '0%';
    document.getElementById('receiveProgressFill').textContent = '0%';
    document.getElementById('receiveSpeed').textContent = '0 MB/s';
}

// Download single file
async function downloadSingleFile(transferId, manifest) {
    downloadAbortController = new AbortController();
    const signal = downloadAbortController.signal;

    const totalChunks = manifest.totalChunks;
    const chunks = [];
    let downloadedChunks = 0;
    let downloadedBytes = 0;
    const startTime = Date.now();
    const maxRetries = 10;
    const retryDelay = 2000;

    try {
        for (let i = 0; i < totalChunks; i++) {
            if (signal.aborted) throw new Error('Cancelled');

            let retries = 0;
            let success = false;

            while (!success && retries < maxRetries) {
                if (signal.aborted) throw new Error('Cancelled');

                try {
                    const response = await fetch(`${RELAY_URL}/transfer/${transferId}/chunk/${i}`, { signal });

                    if (response.ok) {
                        const chunkData = await response.blob();
                        chunks.push(chunkData);

                        downloadedChunks++;
                        downloadedBytes += chunkData.size;

                        const progress = (downloadedChunks / totalChunks) * 100;
                        const elapsed = (Date.now() - startTime) / 1000;
                        const speed = downloadedBytes / elapsed / 1024 / 1024;

                        document.getElementById('receiveProgressFill').style.width = `${progress}%`;
                        document.getElementById('receiveProgressFill').textContent = `${progress.toFixed(1)}%`;
                        document.getElementById('receiveSpeed').textContent = `${speed.toFixed(2)} MB/s`;

                        success = true;
                    } else if (response.status === 404) {
                        retries++;
                        if (retries < maxRetries) {
                            document.getElementById('receiveStatus').textContent = `Waiting for chunk ${i}... (${retries}/${maxRetries})`;
                            await new Promise(resolve => setTimeout(resolve, retryDelay));
                        } else {
                            throw new Error(`Chunk ${i} not available`);
                        }
                    } else {
                        throw new Error(`HTTP ${response.status}`);
                    }
                } catch (error) {
                    if (error.name === 'AbortError' || error.message === 'Cancelled') throw error;

                    if (retries < maxRetries - 1) {
                        retries++;
                        await new Promise(resolve => setTimeout(resolve, retryDelay));
                    } else {
                        throw error;
                    }
                }
            }
        }

        // Download file
        const blob = new Blob(chunks);

        if (window.pywebview) {
            showStatus('receiveStatusMsg', '💾 Saving file...', 'info');
            const reader = new FileReader();
            reader.readAsDataURL(blob);
            reader.onloadend = async function () {
                try {
                    const base64data = reader.result;
                    const result = await window.pywebview.api.save_file(manifest.fileName, base64data);
                    if (result.success) {
                        showStatus('receiveStatusMsg', `✅ Saved to: ${result.path}`, 'success');
                    } else {
                        if (result.reason === "User cancelled") {
                            showStatus('receiveStatusMsg', '⚠️ Save cancelled', 'info');
                        } else {
                            throw new Error(result.reason);
                        }
                    }
                } catch (error) {
                    showStatus('receiveStatusMsg', `❌ Error saving: ${error.message}`, 'error');
                }
            };
        } else {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = manifest.fileName;
            a.click();
            URL.revokeObjectURL(url);
            showStatus('receiveStatusMsg', '✅ Download complete!', 'success');
        }
    } catch (error) {
        if (error.message === 'Cancelled' || error.name === 'AbortError') {
            showStatus('receiveStatusMsg', '🛑 Download cancelled', 'error');
        } else {
            throw error;
        }
    } finally {
        downloadAbortController = null;
    }
}

// Download folder (multiple files) and create ZIP
async function downloadFolder(transferId, manifest) {
    downloadAbortController = new AbortController();
    const signal = downloadAbortController.signal;

    const zip = new JSZip();
    const files = manifest.files;
    const totalFiles = files.length;
    let currentFileIndex = 0;
    let totalDownloadedBytes = 0;
    const startTime = Date.now();
    const maxRetries = 10;
    const retryDelay = 2000;

    // Calculate total chunks across all files
    const totalChunks = files.reduce((sum, f) => sum + f.totalChunks, 0);
    let globalChunkIndex = 0;

    try {
        for (const fileInfo of files) {
            if (signal.aborted) throw new Error('Cancelled');

            currentFileIndex++;
            const fileChunks = [];

            document.getElementById('receiveStatus').textContent = `Downloading file ${currentFileIndex}/${totalFiles}: ${fileInfo.fileName}`;

            for (let i = 0; i < fileInfo.totalChunks; i++) {
                if (signal.aborted) throw new Error('Cancelled');

                let retries = 0;
                let success = false;

                while (!success && retries < maxRetries) {
                    if (signal.aborted) throw new Error('Cancelled');

                    try {
                        const response = await fetch(`${RELAY_URL}/transfer/${transferId}/chunk/${globalChunkIndex}`, { signal });

                        if (response.ok) {
                            const chunkData = await response.blob();
                            fileChunks.push(chunkData);
                            totalDownloadedBytes += chunkData.size;

                            const progress = ((globalChunkIndex + 1) / totalChunks) * 100;
                            const elapsed = (Date.now() - startTime) / 1000;
                            const speed = totalDownloadedBytes / elapsed / 1024 / 1024;

                            document.getElementById('receiveProgressFill').style.width = `${progress}%`;
                            document.getElementById('receiveProgressFill').textContent = `${progress.toFixed(1)}%`;
                            document.getElementById('receiveSpeed').textContent = `${speed.toFixed(2)} MB/s`;

                            success = true;
                            globalChunkIndex++;
                        } else if (response.status === 404) {
                            retries++;
                            if (retries < maxRetries) {
                                document.getElementById('receiveStatus').textContent = `Waiting for chunk ${globalChunkIndex}... (${retries}/${maxRetries})`;
                                await new Promise(resolve => setTimeout(resolve, retryDelay));
                            } else {
                                throw new Error(`Chunk ${globalChunkIndex} not available`);
                            }
                        } else {
                            throw new Error(`HTTP ${response.status}`);
                        }
                    } catch (error) {
                        if (error.name === 'AbortError' || error.message === 'Cancelled') throw error;

                        if (retries < maxRetries - 1) {
                            retries++;
                            await new Promise(resolve => setTimeout(resolve, retryDelay));
                        } else {
                            throw error;
                        }
                    }
                }
            }

            const fileBlob = new Blob(fileChunks);
            const filePath = fileInfo.filePath || fileInfo.fileName;
            zip.file(filePath, fileBlob);
        }

        document.getElementById('receiveStatus').textContent = 'Creating ZIP file...';
        const zipBlob = await zip.generateAsync({
            type: 'blob',
            compression: 'STORE'
        });

        if (window.pywebview) {
            showStatus('receiveStatusMsg', '💾 Saving ZIP...', 'info');
            const reader = new FileReader();
            reader.readAsDataURL(zipBlob);
            reader.onloadend = async function () {
                try {
                    const base64data = reader.result;
                    const fileName = manifest.folderName ? `${manifest.folderName}.zip` : 'download.zip';
                    const result = await window.pywebview.api.save_file(fileName, base64data);
                    if (result.success) {
                        showStatus('receiveStatusMsg', `✅ Saved to: ${result.path}`, 'success');
                    } else {
                        if (result.reason === "User cancelled") {
                            showStatus('receiveStatusMsg', '⚠️ Save cancelled', 'info');
                        } else {
                            throw new Error(result.reason);
                        }
                    }
                } catch (error) {
                    showStatus('receiveStatusMsg', `❌ Error saving: ${error.message}`, 'error');
                }
            };
        } else {
            const url = URL.createObjectURL(zipBlob);
            const a = document.createElement('a');
            a.href = url;
            a.download = manifest.folderName ? `${manifest.folderName}.zip` : 'download.zip';
            a.click();
            URL.revokeObjectURL(url);
            showStatus('receiveStatusMsg', `✅ Downloaded ${totalFiles} files as ZIP!`, 'success');
        }
    } catch (error) {
        if (error.message === 'Cancelled' || error.name === 'AbortError') {
            showStatus('receiveStatusMsg', '🛑 Download cancelled', 'error');
        } else {
            throw error;
        }
    } finally {
        downloadAbortController = null;
    }
}

// Show status message
function showStatus(elementId, message, type) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = `status-message show status-${type}`;
}

// Generate unique ID
function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}
