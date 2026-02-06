"""
Start All Servers - Run all three servers in parallel using Threading
This avoids the 'infinite loop' issue when frozen as an executable.
"""
import uvicorn
import threading
import time
import sys
import os
import signal
from contextlib import contextmanager

# Add current directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import server apps
try:
    from backend.relay_server import app as relay_app
    from backend.signaling_server import app as signaling_app
    from web_server import app as web_app
    from config import RELAY_PORT, SIGNALING_PORT, RELAY_HOST, SIGNALING_HOST
except ImportError as e:
    print(f"!! Import Error: {e}")
    print("Make sure you are running from the project root directory.")
    try:
        input("Press Enter to exit...")
    except:
        pass
    sys.exit(1)

class ServerThread(threading.Thread):
    def __init__(self, app, host, port, name):
        super().__init__()
        self.server = None
        self.app = app
        self.host = host
        self.port = port
        self.name = name
        self.daemon = True # Kill thread when main process exits

    def run(self):
        print(f"Starting {self.name} on {self.host}:{self.port}...")
        config = uvicorn.Config(app=self.app, host=self.host, port=self.port, log_level="info", loop="asyncio")
        self.server = uvicorn.Server(config)
        # Disable signal handlers in threads so main thread can handle Ctrl+C
        self.server.install_signal_handlers = lambda: None
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True

def main():
    # Redirect stdout/stderr when running without console
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        import io
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
    
    print("=" * 60)
    print("Starting Send Anywhere (Production Mode)")
    print("=" * 60)
    print()

    # Create server threads
    relay_thread = ServerThread(relay_app, RELAY_HOST, RELAY_PORT, "Relay Server")
    signaling_thread = ServerThread(signaling_app, SIGNALING_HOST, SIGNALING_PORT, "Signaling Server")
    web_thread = ServerThread(web_app, "0.0.0.0", 5001, "Web UI")

    # Start threads
    relay_thread.start()
    signaling_thread.start()
    web_thread.start()

    # Wait longer for servers to start when running as exe
    time.sleep(8)

    # Get local IP for sharing
    import socket
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    local_ip = get_local_ip()
    network_url = f"http://{local_ip}:5001"

    print()
    print("=" * 60)
    print("All servers running!")
    print("=" * 60)
    print(f"Local:     http://localhost:5001")
    print(f"Network:   {network_url}  <-- Share this link!")
    print("=" * 60)
    print()

    # Open browser automatically (or desktop app window)
    # web_url = "http://localhost:5001"
    # print(f"📱 Opening browser: {web_url}")
    # webbrowser.open(web_url)

    # Create a native window using pywebview
    import webview
    
    # API for JavaScript to talk to Python
    import base64
    class Api:
        def save_file(self, filename, content):
            """Save file from JavaScript"""
            try:
                # Open save dialog
                file_types = ('All files (*.*)',)
                if filename.endswith('.zip'):
                    file_types = ('ZIP files (*.zip)', 'All files (*.*)')
                
                result = window.create_file_dialog(webview.SAVE_DIALOG, save_filename=filename, file_types=file_types)
                
                if result:
                    save_path = result if isinstance(result, str) else result[0]
                    # content is base64 string: "data:application/octet-stream;base64,..."
                    # Remove header if present
                    if ',' in content:
                        content = content.split(',')[1]
                    
                    file_data = base64.b64decode(content)
                    with open(save_path, 'wb') as f:
                        f.write(file_data)
                    return {"success": True, "path": save_path}
                return {"success": False, "reason": "User cancelled"}
            except Exception as e:
                return {"success": False, "reason": str(e)}

        def select_save_file(self, filename):
            """Select a file path for saving a single file"""
            try:
                file_types = ('All files (*.*)',)
                if filename.endswith('.zip'):
                    file_types = ('ZIP files (*.zip)', 'All files (*.*)')
                
                result = window.create_file_dialog(webview.SAVE_DIALOG, save_filename=filename, file_types=file_types)
                
                if result:
                    path = result if isinstance(result, str) else result[0]
                    return {"success": True, "path": path}
                return {"success": False, "reason": "User cancelled"}
            except Exception as e:
                return {"success": False, "reason": str(e)}

        def select_folder(self):
            """Select a folder for saving multiple files"""
            try:
                result = window.create_file_dialog(webview.FOLDER_DIALOG)
                if result:
                    return {"success": True, "path": result[0]}
                return {"success": False, "reason": "User cancelled"}
            except Exception as e:
                return {"success": False, "reason": str(e)}

        def init_file_stream(self, filepath):
            """Initialize a file for writing (clears content)"""
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'wb') as f:
                    pass # Just create/clear file
                return {"success": True}
            except Exception as e:
                return {"success": False, "reason": str(e)}

        def append_chunk(self, filepath, chunk_base64):
            """Append a chunk of data to the file"""
            try:
                # Remove header if present
                if ',' in chunk_base64:
                    chunk_base64 = chunk_base64.split(',')[1]
                
                data = base64.b64decode(chunk_base64)
                with open(filepath, 'ab') as f:
                    f.write(data)
                return {"success": True}
            except Exception as e:
                return {"success": False, "reason": str(e)}

    print(f"Opening Desktop App...")
    
    api = Api()
    
    # Get path to loading screen
    if getattr(sys, 'frozen', False):
        # Running as exe
        base_path = sys._MEIPASS
    else:
        # Running as script
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    loading_path = os.path.join(base_path, 'static', 'loading.html')
    
    # Create window with loading screen first
    window = webview.create_window(
        'Send Anywhere', 
        url=f'file:///{loading_path}',
        width=1000,
        height=700,
        resizable=True,
        min_size=(800, 600),
        js_api=api
    )
    
    # Start webview (this blocks until window is closed)
    webview.start()
    
    # When window closes, stop servers
    print("\nWindow closed, stopping servers...")
    relay_thread.stop()
    signaling_thread.stop()
    web_thread.stop()
    print("Goodbye!")

if __name__ == "__main__":
    # Fix for MP in exe
    import multiprocessing
    multiprocessing.freeze_support()
    main()
