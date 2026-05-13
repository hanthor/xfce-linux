import socket, time

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('127.0.0.1', 4447))
s.settimeout(5.0)

s.sendall(b'journalctl -b | tail -n 200\n')
time.sleep(2)

output = b''
while True:
    try:
        data = s.recv(4096)
        if not data:
            break
        output += data
    except socket.timeout:
        break

print(output.decode('utf-8', errors='replace'))
