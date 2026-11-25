"""D2: concurrent reservation server with conflict detection, expiry and CSV metrics."""
import csv
import json
import os
import socketserver
import threading
import time
import uuid
from pathlib import Path
from sdn_api import install_flow, delete_flow

HOST = os.getenv("SERVER_HOST", "0.0.0.0")
PORT = int(os.getenv("SERVER_PORT", "5000"))
TOTAL_CAPACITY_MBPS = float(os.getenv("TOTAL_CAPACITY_MBPS", "100"))
METRICS_FILE = Path(os.getenv("METRICS_FILE", "metrics.csv"))
reservations = {}
lock = threading.RLock()

if not METRICS_FILE.exists():
    with METRICS_FILE.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["timestamp","event","reservation_id","src_ip","dst_ip","mbps","duration_seconds","response_ms","reason"])

def log_metric(event, item=None, response_ms=0.0, reason=""):
    item = item or {}
    with METRICS_FILE.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([time.time(),event,item.get("id",""),item.get("src_ip",""),item.get("dst_ip",""),item.get("mbps",""),item.get("seconds",""),round(response_ms,3),reason])

def expire_worker():
    while True:
        time.sleep(1)
        now = time.time()
        with lock:
            expired = [rid for rid, item in reservations.items() if item["expires_at"] <= now]
            for rid in expired:
                item = reservations.pop(rid)
                delete_flow(item["src_ip"], item["dst_ip"])
                log_metric("EXPIRED", item, reason="reservation duration elapsed")
                print(f"Expired reservation {rid}; released {item['mbps']} Mbps")

def respond(request):
    started = time.perf_counter()
    action = request.get("action")
    if action == "reserve":
        src, dst = str(request.get("src_ip", "")), str(request.get("dst_ip", ""))
        try:
            mbps, seconds = float(request.get("mbps")), int(request.get("seconds"))
        except (TypeError, ValueError):
            log_metric("REJECTED", response_ms=(time.perf_counter()-started)*1000, reason="invalid numeric fields")
            return {"status":"REJECTED", "reason":"mbps and seconds must be numbers"}
        if not src or not dst or src == dst or mbps <= 0 or seconds <= 0 or seconds > 86400:
            return {"status":"REJECTED", "reason":"invalid IPs, bandwidth or duration (1..86400 seconds allowed)"}
        with lock:
            # The same directional flow may only have one active reservation. This avoids
            # one reservation's expiry deleting another reservation's flow rule.
            conflict = next((r for r in reservations.values() if r["src_ip"] == src and r["dst_ip"] == dst), None)
            if conflict:
                log_metric("REJECTED", response_ms=(time.perf_counter()-started)*1000, reason="flow already reserved")
                return {"status":"REJECTED", "reason":f"flow already reserved by {conflict['id']}"}
            used = sum(r["mbps"] for r in reservations.values())
            if used + mbps > TOTAL_CAPACITY_MBPS:
                log_metric("REJECTED", response_ms=(time.perf_counter()-started)*1000, reason="capacity exceeded")
                return {"status":"REJECTED", "reason":f"capacity exceeded; {TOTAL_CAPACITY_MBPS-used:g} Mbps remains"}
            rid = str(uuid.uuid4())[:8]
            result = install_flow(src, dst, priority=200)
            if not result.get("ok"):
                log_metric("REJECTED", response_ms=(time.perf_counter()-started)*1000, reason="SDN controller unavailable")
                return {"status":"REJECTED", "reason":"SDN controller unavailable or flow installation failed", "details":result.get("error")}
            item = {"id":rid,"src_ip":src,"dst_ip":dst,"mbps":mbps,"seconds":seconds,"created_at":time.time(),"expires_at":time.time()+seconds}
            reservations[rid] = item
            elapsed = (time.perf_counter()-started)*1000
            log_metric("ACCEPTED", item, elapsed)
            return {"status":"ACCEPTED", "reservation_id":rid, "reserved_mbps":mbps, "remaining_mbps":TOTAL_CAPACITY_MBPS-used-mbps, "expires_in_seconds":seconds, "response_ms":round(elapsed,3)}
    if action == "cancel":
        rid = str(request.get("reservation_id", ""))
        with lock:
            item = reservations.pop(rid, None)
            if not item:
                return {"status":"NOT_FOUND", "reason":"reservation ID not found"}
            result = delete_flow(item["src_ip"], item["dst_ip"])
            log_metric("CANCELLED", item, (time.perf_counter()-started)*1000)
            return {"status":"CANCELLED", "reservation_id":rid, "sdn_delete_ok":result.get("ok", False)}
    if action == "list":
        with lock:
            now = time.time()
            active = [{**r,"remaining_seconds":max(0,round(r["expires_at"]-now,1))} for r in reservations.values()]
            used = sum(r["mbps"] for r in reservations.values())
            return {"status":"OK", "total_capacity_mbps":TOTAL_CAPACITY_MBPS,"used_mbps":used,"remaining_mbps":TOTAL_CAPACITY_MBPS-used,"reservations":active}
    if action == "stats":
        with lock:
            used = sum(r["mbps"] for r in reservations.values())
            return {"status":"OK","active_reservations":len(reservations),"total_capacity_mbps":TOTAL_CAPACITY_MBPS,"used_mbps":used,"remaining_mbps":TOTAL_CAPACITY_MBPS-used,"metrics_file":str(METRICS_FILE)}
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
    threading.Thread(target=expire_worker, daemon=True).start()
    print(f"D2 TCP reservation server listening on {HOST}:{PORT}; logical capacity={TOTAL_CAPACITY_MBPS:g} Mbps")
    with Server((HOST, PORT), Handler) as server:
        server.serve_forever()
