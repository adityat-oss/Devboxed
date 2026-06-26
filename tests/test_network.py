import urllib.request
import sys
import os

print("Attempting to connect to 1.1.1.1 (Cloudflare DNS) directly to bypass the proxy...")
try:
    # Use direct IP to bypass DNS and any proxy settings. We use a 3-second timeout.
    req = urllib.request.urlopen('http://1.1.1.1', timeout=3)
    print("FAIL: Network connection succeeded! The Sandbox kernel socket filter is broken.")
    sys.exit(1)
except Exception as e:
    print(f"SUCCESS: Direct connection definitively blocked by OS Sandbox Kernel.")
    print(f"Error detail: {e}")
    sys.exit(0)
