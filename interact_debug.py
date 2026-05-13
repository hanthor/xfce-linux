import socket, time

def run(cmd):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    try:
        s.connect(('127.0.0.1', 4447))
        s.sendall(b'\n\n\n' + cmd.encode() + b'\n')
        time.sleep(2)
        print(s.recv(4096).decode('utf-8', errors='replace'))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        s.close()

run("ls -l /dev/dri")
run("id xfce")
run("ls -l /dev/input")
