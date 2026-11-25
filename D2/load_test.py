"""Small client-side test: submit concurrent reservations and print responses."""
import concurrent.futures
import json
import socket
import time

SERVER = ("127.0.0.1", 5000)

def send(i):
    req = {"action":"reserve", "src_ip":f"10.0.0.{(i%3)+1}", "dst_ip":f"10.0.0.{((i+1)%3)+1}", "mbps":25, "seconds":20}
    start = time.perf_counter()
    try:
        with socket.create_connection(SERVER, timeout=5) as s:
            s.sendall((json.dumps(req)+"\n").encode())
            response = json.loads(s.makefile("r").readline())
        return {"request":i,"elapsed_ms":round((time.perf_counter()-start)*1000,2),"response":response}
    except Exception as exc:
        return {"request":i,"error":str(exc)}

if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for result in pool.map(send, range(8)):
            print(json.dumps(result))
