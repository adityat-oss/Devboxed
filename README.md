# Sandboxed

**Sandboxed** is a native, zero-dependency, macOS kernel-level isolation tool. 

It allows you to safely execute untrusted scripts, run malware analysis, or create completely disposable local development workspaces—without the overhead of Docker or virtual machines. It is powered directly by the macOS Seatbelt (`sandbox-exec`) API and APFS filesystem clones.

## Features

- **Zero Overhead:** Runs natively on the host kernel using `sandbox-exec`. No VMs to boot.
- **APFS Virtual Jails:** Creates instantaneous, zero-storage clones of your target files. Untrusted scripts run against the clone, guaranteeing your original files are never harmed.
- **Zero-Trust Network Proxy:** An asynchronous, interactive proxy server intercepts HTTP/HTTPS traffic from sandboxed apps. It prompts you via a native macOS dialog to explicitly "Allow" or "Deny" tracking telemetry or suspicious API calls in real-time.
- **Dynamic Toolchain Discovery:** Automatically injects your custom developer environments (`~/.nvm`, `~/.cargo`, `~/.pyenv`) into the sandbox so your compilers work flawlessly.
- **DLP Garbage Collector:** Automatically prevents `.env` secrets, massive `node_modules`, and build artifacts from leaking back to your host filesystem when a session ends.

## Architecture: Dual-Mode Execution

Sandboxed offers two distinct entry points tailored to your exact workflow.

### 1. The Sandbox (`./sandbox`)
*Designed for running untrusted scripts, evaluating unfamiliar GitHub repos, and malware analysis.*

- **Path Obfuscation:** The execution jail is deeply hidden in `/var/folders/...`, completely blinding the script to your real host directory structure.
- **Strict Lockdown:** Absolutely blocks developer tools like `git`, `osascript`, and compilers. 
- **Total Network Interception:** All ports (like SSH) are aggressively kernel-blocked. Only port 80/443 are routed through the interactive Proxy Server.

### 2. The Devbox (`./devbox`)
*Designed for daily development. Keeps your host clean and prevents accidental secret leaks.*

- **Visible Workspaces:** The jail is visibly mounted to `~/Sandboxed_Workspaces/MyProject`. You can open your standard host IDE (VS Code, Cursor) directly into this folder with all your themes and extensions.
- **Interactive Shell:** Drops you into a sandboxed `/bin/zsh` terminal.
- **Developer Freedom:** Explicitly allows outbound SSH (Port 22) and execution of `/usr/local/bin` and `/opt/homebrew`, allowing you to run `git push`, `npm`, and `cargo` inside the sandbox.
- **The Ultimate Cleanup:** When you type `exit`, a Sync GUI appears. It automatically flags and unchecks gigabytes of `node_modules` and sensitive `.env` files. When you approve the sync, the garbage is instantly vaporized, leaving your true host directory perfectly pristine.

## Application Compatibility Boundaries

Because Sandboxed uses **Binary Ripping** (extracting the raw UNIX executable from inside an `.app/Contents/MacOS/` folder) to guarantee the kernel natively sandboxes the entire process tree, there is a hard compatibility boundary for GUI applications:

-  **Supported:** Self-contained binaries, CLI tools, and Chromium/WebKit wrappers (like Google Chrome, Brave, and basic Electron apps). These will successfully run under strict kernel isolation.
-  **Unsupported:** Complex macOS-integrated applications (like Adobe Photoshop, Microsoft Word, Logic Pro, or Xcode). These applications rely heavily on macOS `launchd` XPC daemons, App Store entitlements, and deep WindowServer communication tied to the outer `.app` bundle. Stripping the bundle context to enforce kernel security will cause these apps to crash instantly on launch. Do not attempt to sandbox heavy GUI applications.

## Usage

### 0. Start the Proxy Server
Before running any sandbox environments, you must start the Zero-Trust Network Proxy in a separate terminal. Without this, the sandbox will completely block all HTTP/HTTPS traffic instead of intercepting it.

```bash
python3 src/proxy_server.py
# Leave this running in the background to handle intercept dialogs.
```

### 1. Run a strict, untrusted script:
```bash
./sandbox /path/to/suspicious_script.py
```

### 2. Safely view a suspicious media file or document:
```bash
./sandbox suspicious_video.mp4
# Supports: .mp4, .mov, .mkv, .avi, .jpg, .png, .pdf
# Automatically disables all network access and opens in Preview/QuickTime.
```

### 3. Launch an ephemeral, isolated browser session:
```bash
./sandbox "/Applications/Google Chrome.app"
# Spoofs User-Agent, intercepts all telemetry, and strictly confines downloads to ~/Downloads/Sandboxed_Downloads.
```

### 4. Open a disposable Devbox workspace:
```bash
./devbox /path/to/MyProject
```

## Configuration

On your first run, a default configuration file is generated at `~/.sandboxed_config.json`.

```json
{
    "dlp_patterns": [
        ".env",
        ".pem",
        "id_rsa",
        "node_modules",
        "build"
    ],
    "trusted_domains": [
        "registry.npmjs.org",
        "github.com"
    ],
    "custom_mounts": [],
    "trusted_toolchains": [
        "~/.nvm",
        "~/.cargo",
        "~/.pyenv",
        "/Library/Frameworks/Python.framework"
    ]
}
```

- **`dlp_patterns`**: Filenames or directories that the Sync GUI will automatically red-flag and reject when syncing back to the host.
- **`trusted_domains`**: Domains that bypass the interactive proxy prompt and are silently allowed.
- **`custom_mounts`**: Absolute paths to extra host folders you want mounted into the sandbox by default (e.g., `["/Users/Shared/Assets"]`).
- **`trusted_toolchains`**: Absolute paths to your developer toolchains. Because `devbox` strictly isolates the environment, compilers and their libraries will be blocked unless listed here. Add your custom language installations here to ensure they compile without `Operation not permitted` errors.

## Audit Logs
All proxy interactions, including domains you explicitly "Allow" or "Deny" via the AppleScript UI, are permanently recorded in a local SQLite database at `audit.db` in the project root. You can query this database to review historical sandbox network activity.

## Testing the Sandbox

To prove the efficacy of the kernel isolation, we have included a comprehensive malware simulation script in the `tests/` directory. It attempts to scrape your hardware, establish persistence in `~/Library/LaunchAgents`, steal your `~/.ssh` keys, beacon a raw socket to `1.1.1.1`, and spawn a fake password prompt.

To run the simulation natively (**WARNING:** it will succeed and drop a harmless file in your LaunchAgents):
```bash
bash tests/malware_sim.sh
```

To run the simulation safely inside the Sandbox and watch the kernel mathematically block every attack vector:
```bash
./sandbox tests/malware_sim.sh
```
