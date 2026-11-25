#Network Resource Reservation System — D1

This folder is a standalone version of the project. Use **D1** for the initial submission and **D2** for the enhanced final submission.

## Architecture

- `client.py`: simple TCP client; sends one JSON request per TCP connection.
- `server.py`: threaded TCP server, reservation capacity accounting, and responses.
- `sdn_api.py`: installs/removes OpenFlow rules through Ryu's `ofctl_rest` API.
- `mininet_topology.py`: optional 3-host Mininet topology using an OpenFlow 1.3 switch.

## Important accuracy note

This implementation **tracks requested Mbps as logical reserved capacity** and installs/removes per-flow OpenFlow rules. It does **not by itself guarantee or enforce the requested Mbps rate** on the physical/virtual links. Actual per-flow bandwidth enforcement requires additional OVS QoS/queues or OpenFlow meters configured and tested for the specific OVS/Ryu versions. Do not claim strict bandwidth shaping in the demo unless your team adds and verifies it.

## Prerequisites

Use an Ubuntu VM with Mininet and Open vSwitch installed. Install Ryu in a compatible Python environment, and use the standard Ryu `ofctl_rest` app. A common setup is:

```bash
sudo apt update
sudo apt install mininet openvswitch-switch python3-pip -y
python3 -m pip install ryu
```

Ryu can have dependency/version issues on newer Ubuntu/Python versions. If `pip install ryu` fails, use a course-provided compatible environment rather than silently switching controllers.

## Run order

Open separate terminals inside Ubuntu:

**Terminal 1 — controller REST API and OpenFlow listener**

```bash
ryu-manager ryu.app.ofctl_rest
```

The REST API should be reachable at `http://127.0.0.1:8080`; OpenFlow normally listens on port 6653.

**Terminal 2 — Mininet topology**

```bash
sudo python3 mininet_topology.py
```
At the Mininet prompt, test `pingall`. If needed, use `sudo mn -c` after exiting to clean up old Mininet state.

**Terminal 3 — reservation server**

```bash
python3 server.py
```

For D2, the server writes `metrics.csv` in its current working directory.

**Terminal 4 — client**

```bash
python3 client.py
```

Try these commands from the client prompt:

```text
reserve 10.0.0.1 10.0.0.2 40 60
list
reserve 10.0.0.1 10.0.0.3 70 60
cancel <reservation_id>
```

The third request should be rejected if the first 40 Mbps reservation is still active and total capacity is 100 Mbps. D2 also rejects a duplicate reservation for the same directional source/destination flow and expires reservations automatically.

## Client/server placement note

The simple `client.py` defaults to `127.0.0.1:5000`, so it is intended to run on the same Ubuntu VM as the server. To run it inside a Mininet host, update `HOST` in `client.py` to the reachable IP address of the server and ensure routing/firewall rules permit the TCP port. For a straightforward initial demo, run client and server on the VM and demonstrate the SDN flow changes on Mininet hosts.

## Request format

One JSON object per TCP connection, for example:

```json
{"action":"reserve","src_ip":"10.0.0.1","dst_ip":"10.0.0.2","mbps":40,"seconds":60}
```

Supported actions:

- `reserve`: reserve logical capacity and request a flow rule.
- `cancel`: cancel a reservation by ID.
- `list`: list active reservations.
- `stats`: D2 only; summarize current usage.

## Deliverable checklist

- Include source files, topology, setup steps, screenshots/logs of tests, and a clear architecture diagram in your final GitHub repository.
- Test both accepted and rejected requests, controller unavailable, duplicate flow (D2), cancellation, expiry (D2), and multiple concurrent clients.
- Compare static/baseline behavior with dynamic reservation handling for D2 and record the method and measurements.
