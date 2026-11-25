"""D1: basic threaded TCP reservation server with capacity checks."""
import json
import os
import socketserver
import threading
import time
import uuid
from sdn_api import install_flow, delete_flow

HOST = os.getenv("SERVER_HOST", "0.0.0.0")
PORT = int(os.getenv("SERVER_PORT", "5000"))
TOTAL_CAPACITY_MBPS = float(os.getenv("TOTAL_CAPACITY_MBPS", "100"))
reservations = {}
lock = threading.Lock()

def respond(request):
    action = request.get("action")
    if action == "reserve":
        src, dst = request.get("src_ip"), request.get("dst_ip")
        try:
            mbps, seconds = float(request.get("mbps")), int(request.get("seconds"))
        except (TypeError, ValueError):
            return {"status":"REJECTED", "reason":"mbps and seconds must be numbers"}
        if not src or not dst or src == dst or mbps <= 0 or seconds <= 0:
            return {"status":"REJECTED", "reason":"invalid IPs, bandwidth or duration"}
        with lock:
            used = sum(r["mbps"] for r in reservations.values())
            if used + mbps > TOTAL_CAPACITY_MBPS:
                return {"status":"REJECTED", "reason":f"capacity exceeded; {TOTAL_CAPACITY_MBPS-used:g} Mbps remains"}
            rid = str(uuid.uuid4())[:8]
            result = install_flow(src, dst)
            if not result.get("ok"):
                return {"status":"REJECTED", "reason":"SDN controller unavailable or flow installation failed", "details":result.get("error")}
            reservations[rid] = {"id":rid,"src_ip":src,"dst_ip":dst,"mbps":mbps,"seconds":seconds,"created":time.time()}
            return {"status":"ACCEPTED", "reservation_id":rid, "reserved_mbps":mbps, "remaining_mbps":TOTAL_CAPACITY_MBPS-used-mbps, "note":"capacity is tracked logically; see README for enforcement limits"}
    if action == "cancel":
        rid = str(request.get("reservation_id", ""))
        with lock:
            item = reservations.pop(rid, None)
            if not item:
                return {"status":"NOT_FOUND", "reason":"reservation ID not found"}
            delete_flow(item["src_ip"], item["dst_ip"])
            return {"status":"CANCELLED", "reservation_id":rid}
    if action == "list":
        with lock:
            return {"status":"OK", "total_capacity_mbps":TOTAL_CAPACITY_MBPS, "reservations":list(reservations.values())}
    return {"status":"REJECTED", "reason":"unknown action"}

class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        line = self.rfile.readline(65536)
        try:
            request = json.loads(line.decode("utf-8"))
            result = respond(request)
        except (json.JSONDecodeError, UnicodeDecodeError):
            result = {"status":"REJECTED", "reason":"send one valid JSON object per line"}
        self.wfile.write((json.dumps(result) + "\n").encode("utf-8"))

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == "__main__":
    print(f"TCP reservation server listening on {HOST}:{PORT}; logical capacity={TOTAL_CAPACITY_MBPS:g} Mbps")
    with Server((HOST, PORT), Handler) as server:
        server.serve_forever()
