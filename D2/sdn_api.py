"""Helpers for Ryu's standard ofctl_rest API."""
import json
import os
import urllib.request
import urllib.error

CONTROLLER_URL = os.getenv("SDN_REST_URL", "http://127.0.0.1:8080")
DPID = int(os.getenv("SDN_DPID", "1"))

def _post(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(CONTROLLER_URL + path, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            body = response.read().decode("utf-8", errors="replace")
            return {"ok": True, "status": response.status, "body": body}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "error": str(exc)}

def install_flow(src_ip, dst_ip, priority=100):
    payload = {
        "dpid": DPID, "table_id": 0, "priority": priority,
        "idle_timeout": 0, "hard_timeout": 0,
        "match": {"eth_type": 2048, "ipv4_src": src_ip, "ipv4_dst": dst_ip},
        "actions": [{"type": "OUTPUT", "port": "NORMAL"}]
    }
    return _post("/stats/flowentry/add", payload)

def delete_flow(src_ip, dst_ip):
    payload = {
        "dpid": DPID, "table_id": 0, "command": "DELETE",
        "match": {"eth_type": 2048, "ipv4_src": src_ip, "ipv4_dst": dst_ip},
        "actions": []
    }
    return _post("/stats/flowentry/delete", payload)
