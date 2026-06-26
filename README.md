# Devboxed

**Devboxed** is a native, zero-dependency, macOS kernel-level isolation tool. 

It allows you to safely execute untrusted scripts, run malware analysis, or create completely disposable local development workspaces—without the heavy overhead of Docker or virtual machines. It is powered directly by the macOS Seatbelt (`sandbox-exec`) kernel API and instantaneous APFS filesystem clones.

## Features

- **Zero Overhead:** Runs natively on the host kernel using `sandbox-exec`. No VMs to boot. No containers to configure.
- **Zero-Trust Network Proxy:** An asynchronous, interactive proxy server intercepts HTTP/HTTPS traffic from sandboxed apps. It prompts you via a native macOS dialog to explicitly "Allow" or "Deny" tracking telemetry or suspicious API calls in real-time.
- **Dynamic Toolchain Discovery:** Automatically injects your custom developer environments (`~/.nvm`, `~/.cargo`, `~/.pyenv`) into the sandbox so your compilers work flawlessly.
- **DLP Garbage Collector:** Automatically prevents `.env` secrets, massive `node_modules`, and build artifacts from leaking back to your host filesystem when a session ends.
- **Cyberpunk UI & IDE Auto-Routing:** Instantly launches your host IDE (VSCode/Cursor) directly into the virtual jail. When you exit, a breathtaking Dark Mode native GUI diff viewer prompts you to safely sync your code changes.

## Setup Guide (Quick Start)

To install and test Sandboxed immediately, simply copy and paste the following commands into your terminal:

```bash
# 1. Clone the repository and enter the directory
git clone https://github.com/my_username/Sandboxed.git
cd Sandboxed

# 2. Run the global installer
./install.sh
```

*(**Security Note:** `install.sh` does not download any external dependencies, daemonize any processes, or modify your system state. It simply creates two symbolic links in `/usr/local/bin/` pointing to the scripts, and generates a default JSON configuration file in your home directory.)*

**What to expect if it worked:**
- You will see a success message indicating that `devbox` and `sandbox` have been linked to `/usr/local/bin`.
- A default configuration file will be generated at `~/.sandboxed_config.json`.
- **Note:** If you want the Network Interceptor to work, you must keep the proxy server running in a background terminal by executing: `python3 src/proxy_server.py`.

## Architecture: Dual-Mode Execution

Sandboxed offers two distinct entry points tailored to your exact workflow.

### 1. The Sandbox (`sandbox`)
*Designed for running untrusted scripts, evaluating unfamiliar GitHub repos, and malware analysis.*

- **Path Obfuscation:** The execution jail is deeply hidden in `/var/folders/...`, completely blinding the script to your real host directory structure.
- **Strict Lockdown:** Absolutely blocks developer tools like `osascript`, reads to `~/.ssh`, and any modifications to your host filesystem.
- **Total Network Interception:** All ports (like SSH) are aggressively kernel-blocked. Only port 80/443 are routed through the interactive Proxy Server.

### 2. The Devbox (`devbox`)
*Designed as the ultimate "Undo Switch" for trusted daily development.*

- **The Undo Switch:** `devbox` allows full read/execution/network access so tools like Git, SSH, npm, and compilers work perfectly. However, it enforces a strict `(deny file-write*)` against your entire Host directory, guaranteeing that your Host machine cannot be changed accidentally.
- **Visible Workspaces:** The jail is visibly mounted to `~/Sandboxed_Workspaces/MyProject` for seamless integration.
- **Interactive Shell:** Drops you into a sandboxed `/bin/zsh` terminal.

### 3. Global Caches & Virtual Environments
A critical part of the Devbox "Undo Switch" is how it handles dependencies and downloads:
- **Inside the Project (`venv`, `node_modules`):** If you create a virtual environment inside the project folder and download gigabytes of packages, it succeeds. When you exit Devbox, you can easily discard the `venv` folder using the Sync GUI, and it gets permanently vaporized.
- **Outside the Project (`~/.cache/huggingface`, global `npm`):** If a script attempts to download a massive HuggingFace LLM to your global `~/.cache` directory, the macOS kernel will **instantly block the download** with an `Operation not permitted` error. Devbox forbids bloated caches from accumulating on your host machine.

### 4. Cache Spoofing (Automatic Redirection)
To allow global caching tools to work seamlessly while still being vaporized on exit, Devbox automatically "spoofs" caching environment variables.

In your `~/.sandboxed_config.json`, you will see a `devbox_env_vars` dictionary. By default, it aggressively redirects common cache directories into a `.devbox_caches` folder *inside* your virtual jail:
```json
    "devbox_env_vars": {
        "HF_HOME": "./.devbox_caches/huggingface",
        "PIP_CACHE_DIR": "./.devbox_caches/pip",
        "NPM_CONFIG_CACHE": "./.devbox_caches/npm",
        "XDG_CACHE_HOME": "./.devbox_caches/xdg",
        "CARGO_HOME": "./.devbox_caches/cargo"
    }
```
*How it works:* Any path starting with `./` is automatically converted into an absolute path inside the Virtual Jail. When a tool like `npm` tries to cache a file globally, the spoofed variable forces it to download into the isolated `.devbox_caches` folder instead. When you exit Devbox, those bloated caches are effortlessly deleted along with the rest of the jail!

*(**Finding Your Dependencies:** If an application crashes inside Devbox with an `Operation not permitted` error, check its documentation to see where it caches files globally. Then, simply add its specific Environment Variable (e.g., `GOCACHE`) to your `devbox_env_vars` config and map it to `./.devbox_caches/go` to instantly fix it!)*

## Usage

### 1. Start the Proxy Server (Optional but Recommended)
Before running environments that require network proxying, start the proxy in a separate terminal:
```bash
python3 src/proxy_server.py
```

### 2. Open a disposable Devbox workspace:
```bash
devbox /path/to/MyProject
```
*(This instantly clones your folder, drops you into a secure shell, and auto-launches your IDE into the jail.)*

### 3. Run a strict, untrusted script:
```bash
sandbox /path/to/suspicious_script.py
```

### 4. Launch an ephemeral, isolated browser session:
```bash
sandbox "/Applications/Google Chrome.app"
# Spoofs User-Agent, intercepts all telemetry, and strictly confines downloads to ~/Downloads/Sandboxed_Downloads.
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
- **`custom_mounts`**: Absolute paths to extra host folders you want mounted into the sandbox by default.
- **`trusted_toolchains`**: Absolute paths to your developer toolchains. Since `sandbox` strictly isolates the environment, compilers will be blocked unless listed here.

## Testing the Sandbox

To prove the efficacy of the kernel isolation, we have included a comprehensive malware simulation script in the `tests/` directory. It attempts to scrape your hardware, establish persistence in `~/Library/LaunchAgents`, steal your `~/.ssh` keys, beacon a raw socket to `1.1.1.1`, and spawn a fake password prompt.

To run the simulation safely inside the Sandbox and watch the kernel mathematically block every attack vector:
```bash
sandbox tests/malware_sim.sh
```
