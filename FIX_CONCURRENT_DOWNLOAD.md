"""
Fix for concurrent upload/download issue:
The receiver should wait for upload to complete before starting download.
"""

# Add this to app.js - wait for upload completion before allowing download

// In startReceive function, check transfer status first:

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
        const transferId = pairInfo.transfer_id;
        
        // Display file info
        if (manifest.type === 'file') {
            document.getElementById('receiveFileName').textContent = manifest.fileName;
            document.getElementById('receiveFileSize').textContent = formatSize(manifest.size);
            document.getElementById('receiveChunks').textContent = manifest.totalChunks;
        } else {
            document.getElementById('receiveFileName').textContent = `${manifest.totalFiles} files`;
            document.getElementById('receiveFileSize').textContent = formatSize(manifest.totalSize);
            const totalChunks = manifest.files.reduce((sum, f) => sum + f.totalChunks, 0);
            document.getElementById('receiveChunks').textContent = totalChunks;
        }
        
        document.getElementById('receiveFileInfo').classList.add('show');
        
        // WAIT FOR UPLOAD TO COMPLETE
        showStatus('receiveStatusMsg', 'Waiting for sender to complete upload...', 'info');
        
        const totalChunks = manifest.type === 'file' ? manifest.totalChunks : manifest.files.reduce((sum, f) => sum + f.totalChunks, 0);
        
        // Poll status until upload is complete
        while (true) {
            const statusResponse = await fetch(`${RELAY_URL}/transfer/${transferId}/status`);
            const status = await statusResponse.json();
            
            showStatus('receiveStatusMsg', `Upload progress: ${status.progress.toFixed(1)}% (${status.uploaded_chunks}/${status.total_chunks} chunks)`, 'info');
            
            if (status.complete) {
                break;
            }
            
            // Wait 2 seconds before checking again
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
        
        showStatus('receiveStatusMsg', 'Upload complete! Starting download...', 'success');
        
        // Now download
        await downloadFromRelay(transferId, manifest);
        
    } catch (error) {
        showStatus('receiveStatusMsg', `Error: ${error.message}`, 'error');
    }
}
