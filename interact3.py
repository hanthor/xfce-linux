import socket, time, sys

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', 4447))
    s.settimeout(2.0)
    
    s.sendall(b'journalctl -b | grep -i -E "gdm|xfce|wayland|error|fail" | tail -n 100\n')
    time.sleep(1.0)
    
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
except Exception as e:
    print(f"Error: {e}")
