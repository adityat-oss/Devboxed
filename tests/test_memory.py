import sys
import time

print("Attempting to allocate 2GB of RAM to simulate a memory-exhaustion attack...")
try:
    # Allocate 2GB of data
    x = bytearray(2 * 1024 * 1024 * 1024)
    print("FAIL: Memory allocation succeeded! Sandbox quotas are broken.")
    sys.exit(1)
except MemoryError:
    print("SUCCESS: Memory allocation strictly blocked by OS Quota (MemoryError).")
    sys.exit(0)
except BaseException as e:
    print(f"SUCCESS: Process immediately killed by OS Quota. Error detail: {e}")
    sys.exit(0)
