from scapy.all import IP, UDP, TCP, ICMP, Raw

def create_probe(target, ttl, proto, port, size):
    # Instructions require adjustable packet size
    payload = Raw(load="X" * size) 
    ip_layer = IP(dst=target, ttl=ttl)

    if proto.upper() == "TCP":
        # TCP SYN is a standard way to probe a port
        return ip_layer / TCP(dport=port, flags="S") / payload
    elif proto.upper() == "UDP":
        return ip_layer / UDP(dport=port) / payload
    elif proto.upper() == "ICMP":
        return ip_layer / ICMP() / payload
    else:
        raise ValueError(f"Unsupported protocol: {proto}")