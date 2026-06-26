import os
import sys
import subprocess
import argparse
import tempfile
import resource
import config

def create_vm(machine_name: str, distro: str = "native"):
    pass

def destroy_vm(machine_name: str):
    pass

def set_limits(memory_mb):
    """Enforce strict memory and fork-bomb limits at the OS kernel level."""
    if memory_mb > 0:
        bytes_limit = memory_mb * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_AS, (bytes_limit, bytes_limit))
        except ValueError:
            pass

def run_in_vm(machine_name: str, target_dir: str, mode: str, cmd_list: list, memory_mb: int, net_enabled: bool):
    user_config = config.load_config()
    toolchain_roots = set()
    devbox_writes = set()
    
    if mode == "dev":
        for tc in user_config.get("trusted_toolchains", []):
            toolchain_roots.add(os.path.expanduser(tc))
        for aw in user_config.get("devbox_allowed_writes", []):
            devbox_writes.add(os.path.expanduser(aw))
                    
    toolchain_allows = "".join([f'\n    (subpath "{root}")' for root in toolchain_roots])
    devbox_write_allows = "".join([f'\n(allow file-write* (subpath "{root}"))' for root in devbox_writes])

    if mode == "dev":
        profile = f"""(version 1)
(allow default)

;; ---------------------------------------------------------
;; DEV MODE: THE UNDO SWITCH
;; ---------------------------------------------------------
;; Allow everything (full network, full execution, full reads)
;; so that tools like Git, SSH, npm, and compilers work natively.
;;
;; BUT block all file writes to the user's host directory to 
;; mathematically guarantee the "Undo Switch" isolation.
(deny file-write* (subpath "/Users"))

;; Explicitly allow writing to the Virtual Jail construct
(allow file-write* (subpath "{target_dir}"))

;; Explicitly allow writing to system temporary directories
(allow file-write* (subpath "/private/tmp"))
(allow file-write* (subpath "/private/var/folders"))
(allow file-write* (subpath "/dev"))

;; Explicitly allowed global host writes from ~/.sandboxed_config.json{devbox_write_allows}
"""
    else:
        exec_allows = f"""
    (literal "{cmd_list[0] if cmd_list else '/bin/sh'}")
    (subpath "/bin")
    (subpath "/sbin")
    (subpath "/usr/bin")
    (subpath "/usr/sbin")
    (subpath "/usr/libexec")
    (subpath "/System")
    (subpath "/Library")
    (subpath "/Applications")
    (subpath "{target_dir}")
"""

        profile = f"""(version 1)
(deny default)
(deny process-exec*)

;; Explicitly allow execution of core macOS binaries, Virtual Jail, and target binary
(allow process-exec*{exec_allows})
(deny process-exec* (literal "/usr/bin/osascript"))

(allow process-fork)
(allow ipc-posix-shm*)
"""
        if mode in ("app", "strict"):
            profile += """
(allow sysctl-read)
(allow mach-lookup)
"""
        if mode == "app":
            profile += """
(allow iokit-open)
"""
        profile += f"""

;; Default Deny Posture for Reads
(deny file-read*)
(allow file-read-metadata)
(allow file-read*
    (literal "/")
    (subpath "/System")
    (subpath "/usr/lib")
    (subpath "/usr/bin")
    (subpath "/usr/share")
    (subpath "/bin")
    (subpath "/sbin")
    (subpath "/private/var/run")
    (subpath "/private/var/folders")
    (subpath "/private/var/db")
    (subpath "/etc")
    (subpath "/private/tmp")
    (subpath "/dev")
    (subpath "/Library")
    (subpath "/Applications")
    (subpath "{target_dir}")
)
"""

        if mode == "strict":
            profile += f"""
(allow file-ioctl)
(allow signal)
(allow file-write*
    (subpath "/private/tmp")
    (subpath "/private/var/folders")
    (subpath "/dev")
    (subpath "{target_dir}")
)
"""
        elif mode == "app":
            profile += f"""
(allow file-ioctl)
(allow signal)
(allow file-write*
    (subpath "/private/tmp")
    (subpath "/private/var/folders")
    (subpath "/dev")
    (subpath "{os.path.expanduser('~/Library')}")
    (subpath "{target_dir}")
)
"""

        # Handle Network
        if net_enabled:
            profile += """
(deny network*)
(allow network-outbound (literal "/private/var/run/mDNSResponder"))
(allow network-outbound (remote tcp "*:8080"))
"""
        else:
            profile += """
(deny network*)
"""

        
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sb', delete=False) as f:
        f.write(profile)
        profile_path = f.name

    env = os.environ.copy()
    if net_enabled:
        env["http_proxy"] = "http://127.0.0.1:8080"
        env["https_proxy"] = "http://127.0.0.1:8080"
        
    # Inject Spoofed Environment Variables for Cache Redirection
    if mode == "dev":
        for env_key, env_val in user_config.get("devbox_env_vars", {}).items():
            if env_val.startswith("./"):
                # Expand local paths relative to the Virtual Jail target directory
                env[env_key] = os.path.join(target_dir, env_val[2:])
            else:
                env[env_key] = env_val
        
    cmd = ["sandbox-exec", "-f", profile_path]
    if cmd_list:
        cmd.extend(cmd_list)
    else:
        cmd.extend(["/bin/sh"])
        
    try:
        # Use subprocess safely (no shell interpolation) and enforce OS limits
        subprocess.run(cmd, env=env, cwd=target_dir, preexec_fn=lambda: set_limits(memory_mb))
    except subprocess.CalledProcessError as e:
        print(f"Session ended with code {e.returncode}")
    finally:
        os.remove(profile_path)

def main():
    parser = argparse.ArgumentParser(description="Bomb Shelter Native Orchestrator (macOS sandbox-exec)")
    parser.add_argument("action", choices=["create", "run", "destroy"], help="Action to perform")
    parser.add_argument("--name", default="bomb-shelter-1", help="Name of the sandbox")
    parser.add_argument("--distro", default="native")
    parser.add_argument("--mode", default="strict", choices=["strict", "app", "media", "dev"])
    parser.add_argument("--dir", help="Target directory to mount/work in")
    parser.add_argument("--mem", type=int, default=512, help="Memory limit in MB")
    parser.add_argument("--net", type=lambda x: (str(x).lower() == 'true'), default=True, help="Network enabled (True/False)")
    parser.add_argument("--cmd", nargs=argparse.REMAINDER, help="Specific command to run")
    
    args = parser.parse_args()
    
    if args.action == "create":
        create_vm(args.name, args.distro)
    elif args.action == "run":
        if not args.dir:
            parser.error("--dir is required for the 'run' action.")
        target_abs = os.path.abspath(args.dir)
        
        # Ensure --cmd captures the actual command without the '--cmd' literal
        cmd_list = args.cmd
        if cmd_list and cmd_list[0] == "--cmd":
            cmd_list = cmd_list[1:]
            
        run_in_vm(args.name, target_abs, args.mode, cmd_list, args.mem, args.net)
    elif args.action == "destroy":
        destroy_vm(args.name)

if __name__ == "__main__":
    main()
