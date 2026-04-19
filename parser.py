import socket
from scapy.all import ICMP, IP

def send_and_parse(response, protocol, rtt, ttl, original_target):
    if response is None:
        return {"ip": None, "name": "*", "rtt": 0.0, "is_destination": False}

    sender_ip = response.src
    
    # DNS Resolution as required by project
    try:
        hostname = socket.gethostbyaddr(sender_ip)[0]
    except (socket.herror, socket.gaierror, Exception):
        hostname = "Unknown"

    # Logic to determine if the trace should stop
    is_destination = False
    if sender_ip == original_target:
        is_destination = True
    elif response.haslayer(ICMP):
        # Type 3 = Port Unreachable (UDP/TCP success), Type 0 = Echo Reply (ICMP success)
        if response[ICMP].type in [0, 3]:
            is_destination = True

    return {
        "ip": sender_ip,
        "name": hostname,
        "rtt": round(rtt, 2),
        "is_destination": is_destination,
        "protocol": protocol,
        "ttl": ttl
    }