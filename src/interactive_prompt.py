import subprocess
import shlex
import sys

def ask_user(domain: str) -> bool:
    """Uses osascript to prompt the user to allow or deny a domain."""
    prompt_text = f"The Sandboxed environment is requesting network access to: {domain}\n\nDo you want to Allow or Deny this connection?"
    
    script = f'''
    display dialog {shlex.quote(prompt_text)} buttons {{"Deny", "Allow"}} default button "Deny" with title "Sandboxed: Network Intercept" with icon caution
    return button returned of result
    '''
    
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=True)
        return "Allow" in result.stdout
    except subprocess.CalledProcessError:
        # If the user clicks cancel, or it times out, deny by default
        return False

if __name__ == "__main__":
    domain = sys.argv[1] if len(sys.argv) > 1 else "example.com"
    allowed = ask_user(domain)
    print(f"Allowed: {allowed}")
