import os
import shutil
import tempfile
import subprocess
import uuid

class VirtualJail:
    def __init__(self, workspace_dir=None):
        # Create a secure Virtual Jail folder
        if workspace_dir:
            self.jail_dir = os.path.abspath(workspace_dir)
        else:
            jail_name = f"sandbox_jail_{uuid.uuid4().hex[:8]}"
            self.jail_dir = os.path.join(tempfile.gettempdir(), jail_name)
            
        os.makedirs(self.jail_dir, exist_ok=True)
        self.mounts = {} # original_path -> jail_path
        
    def mount(self, original_path):
        """Clones a file into the Jail using APFS clonefile for path obfuscation."""
        original_path = os.path.abspath(original_path)
        if not os.path.exists(original_path):
            raise FileNotFoundError(f"File or directory not found: {original_path}")
            
        basename = os.path.basename(original_path)
        jail_path = os.path.join(self.jail_dir, basename)
        
        # Handle naming collisions in the flat Jail root
        counter = 1
        while os.path.exists(jail_path):
            jail_path = os.path.join(self.jail_dir, f"{basename}_{counter}")
            counter += 1
            
        # Use cp -c (clonefile) for instant zero-storage copy
        try:
            subprocess.run(["cp", "-c", "-R", original_path, jail_path], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            # Fallback to standard copy if APFS clonefile is unsupported on this volume
            subprocess.run(["cp", "-R", original_path, jail_path], check=True)
            
        self.mounts[original_path] = jail_path
        return jail_path
        
    def is_text_file(self, filepath):
        try:
            with open(filepath, 'tr') as check_file:
                check_file.read(1024)
                return True
        except Exception:
            return False
            

    def devbox_sync(self, original_path):
        """Launches the SyncGUI to select which files to sync back to the host, skipping DLP flagged items by default."""
        sync_gui = os.path.join(os.path.dirname(__file__), "sync_gui.py")
        jail_path = self.mounts.get(os.path.abspath(original_path))
        if jail_path and os.path.isdir(jail_path):
            subprocess.run(["python3", sync_gui, original_path, jail_path], stderr=subprocess.DEVNULL)
            
    def destroy(self):
        """Eradicate the Virtual Jail."""
        if os.path.exists(self.jail_dir):
            shutil.rmtree(self.jail_dir, ignore_errors=True)
