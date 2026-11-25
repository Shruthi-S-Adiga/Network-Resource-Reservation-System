import json
import socket
import sys

HOST = "127.0.0.1"
PORT = 5000

def main():
    print("Network Resource Reservation Client")
    print("Commands: reserve <src_ip> <dst_ip> <mbps> <seconds> | cancel <reservation_id> | list | quit")
    while True:
        try:
            command = input("reservation> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if command.lower() in ("quit", "exit"):
            break
        parts = command.split()
        if not parts:
            continue
        try:
            if parts[0].lower() == "reserve" and len(parts) == 5:
                request = {"action":"reserve", "src_ip":parts[1], "dst_ip":parts[2], "mbps":float(parts[3]), "seconds":int(parts[4])}
            elif parts[0].lower() == "cancel" and len(parts) == 2:
                request = {"action":"cancel", "reservation_id":parts[1]}
            elif parts[0].lower() == "list" and len(parts) == 1:
                request = {"action":"list"}
            else:
                print("Use: reserve <src_ip> <dst_ip> <mbps> <seconds> | cancel <id> | list | quit")
                continue
            with socket.create_connection((HOST, PORT), timeout=5) as sock:
                sock.sendall((json.dumps(request) + "\n").encode())
                file = sock.makefile("r", encoding="utf-8")
                print(file.readline().strip())
        except (OSError, ValueError) as exc:
            print("Request failed:", exc)

if __name__ == "__main__":
    main()
