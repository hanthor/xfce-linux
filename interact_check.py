import socket, time

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('127.0.0.1', 4447))
s.settimeout(2.0)
s.sendall(b'\njournalctl -b | grep -i xfwl4 | tail -n 20\n')
time.sleep(1)
print(s.recv(4096).decode('utf-8', errors='replace'))
s.close()
