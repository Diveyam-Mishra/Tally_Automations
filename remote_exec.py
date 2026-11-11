import sys
import os
import paramiko

# Read credentials from environment or fallback
REMOTE_HOST = os.environ.get('REMOTE_TALLY_HOST', '100.103.81.73')
REMOTE_PORT = int(os.environ.get('REMOTE_TALLY_SSH_PORT', '22'))
REMOTE_USER = os.environ.get('REMOTE_TALLY_USER', 'ayush')
REMOTE_PASS = os.environ.get('REMOTE_TALLY_PASS', 'Agni@1222')

def run_remote(command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(REMOTE_HOST, port=REMOTE_PORT, username=REMOTE_USER, password=REMOTE_PASS, timeout=15)
        stdin, stdout, stderr = ssh.exec_command(command)
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        if out:
            print(out)
        if err:
            print("STDERR:", err, file=sys.stderr)
        ssh.close()
    except Exception as e:
        print(f"Connection failed: {e}", file=sys.stderr)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python remote_exec.py \"<command>\"")
        sys.exit(1)
    run_remote(" ".join(sys.argv[1:]))
