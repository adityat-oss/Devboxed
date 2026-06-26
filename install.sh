#!/bin/bash
set -e

echo "========================================="
echo "   Sandboxed: Global Installation"
echo "========================================="

# Get the absolute path of the directory this script is in
INSTALL_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Ensure the scripts are executable
chmod +x "$INSTALL_DIR/devbox"
chmod +x "$INSTALL_DIR/sandbox"

# Create absolute symlinks in /usr/local/bin
echo "[*] Creating absolute symlink for 'devbox'..."
sudo ln -sf "$INSTALL_DIR/devbox" /usr/local/bin/devbox

echo "[*] Creating absolute symlink for 'sandbox'..."
sudo ln -sf "$INSTALL_DIR/sandbox" /usr/local/bin/sandbox

echo "[*] Installation complete!"
echo ""
echo "You can now run 'devbox' or 'sandbox' from any directory on your Mac."
echo "If you type 'devbox' with no arguments, it will automatically sandbox your current directory."
echo "========================================="
