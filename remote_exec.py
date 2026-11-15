import sys
import os
import threading
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

        out_chunks, err_chunks = [], []
        def read_stream(stream, chunks):
            try:
                for line in iter(stream.readline, ""):
                    chunks.append(line)
            except Exception:
                pass

        t1 = threading.Thread(target=read_stream, args=(stdout, out_chunks))
        t2 = threading.Thread(target=read_stream, args=(stderr, err_chunks))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        out = "".join(out_chunks)
        err = "".join(err_chunks)
        if out:
            print(out, end="")
        if err:
            print(err, file=sys.stderr, end="")
        ssh.close()
    except Exception as e:
        print(f"Connection failed: {e}", file=sys.stderr)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python remote_exec.py \"<command>\"")
        sys.exit(1)
    run_remote(" ".join(sys.argv[1:]))
