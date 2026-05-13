import socket, time

def run(cmd):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', 4447))
    s.settimeout(2.0)
    s.sendall(b'\n' + cmd.encode() + b'\n')
    time.sleep(1)
    output = b''
    while True:
        try:
            data = s.recv(4096)
            if not data: break
            output += data
        except: break
    print(output.decode('utf-8', errors='replace'))
    s.close()

run("cat /etc/ld.so.conf")
run("ls /etc/ld.so.conf.d")
run("ldconfig -p | grep libxfce4kbd")
