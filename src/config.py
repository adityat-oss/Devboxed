import os
import json

CONFIG_PATH = os.path.expanduser("~/.sandboxed_config.json")

DEFAULT_CONFIG = {
    "dlp_patterns": [".env", ".pem", "id_rsa", "node_modules", "build"],
    "trusted_domains": [],
    "custom_mounts": [],
    "trusted_toolchains": [
        "~/.nvm",
        "~/.cargo",
        "~/.pyenv",
        "/Library/Frameworks/Python.framework"
    ]
}

def load_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG
        
    try:
        with open(CONFIG_PATH, "r") as f:
            user_config = json.load(f)
            # Merge with defaults
            config = DEFAULT_CONFIG.copy()
            config.update(user_config)
            return config
    except Exception as e:
        print(f"Warning: Failed to parse {CONFIG_PATH}: {e}")
        return DEFAULT_CONFIG
