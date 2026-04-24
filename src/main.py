import time
import json
import argparse
import os
import sys
import ipaddress
import requests
from scapy.all import sr1
from packets import create_probe
from parser import send_and_parse

#Function to get geographic coordinates
def get_geo_data(ip):
    if not ip or ip == "*":
        return {"lat": None, "lon": None, "city": "Internal Network"}
    try:
        addr = ipaddress.ip_address(ip)
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            return {"lat": None, "lon": None, "city": "Internal Network"}
    except ValueError:
        pass
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=2).json()
        if response.get("status") == "success":
            return {
                "lat": response.get("lat"),
                "lon": response.get("lon"),
                "city": response.get("city"),
                "country": response.get("country")
            }
    except Exception:
        pass
    return {"lat": None, "lon": None, "city": "Unknown"}

def traceroute(target_ip, args):
    results = []
    print(f"\n--- Tracing {target_ip} (Max TTL: {args.max_ttl}) ---")

    for ttl in range(args.min_ttl, args.max_ttl + 1):
        ttl_results = []
        reached_destination = False

        for _ in range(args.num_series):
            #Sending UDP, TCP, and ICMP per series
            for protocol in ["UDP", "TCP", "ICMP"]:
                packet = create_probe(target_ip, ttl, protocol, args.port, args.size)
                
                start = time.perf_counter()
                response = sr1(packet, timeout=args.timeout, verbose=0)
                end = time.perf_counter()
                
                result = send_and_parse(response, protocol, (end - start) * 1000, ttl, target_ip)
                
                if result["ip"]:
                    result["geo"] = get_geo_data(result["ip"])
                else:
                    result["geo"] = {"lat": None, "lon": None, "city": "Unknown"}

                ttl_results.append(result)

                status = f"{result['ip']} ({result['name']})" if result['ip'] else "*"
                print(f"TTL {ttl} | {protocol:4}: {status:30} - {result['rtt']}ms")

                if result["is_destination"]:
                    reached_destination = True
                
                time.sleep(args.wait)

        results.append(ttl_results)
        if reached_destination:
            print(f"✅ Reached {target_ip}")
            break
    return results

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Error: This script requires root privileges. Please run with 'sudo'.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Internet Topology Explorer")
    parser.add_argument("input_file", help="TXT or CSV file containing list of IPs")
    parser.add_argument("-m", "--max_ttl", type=int, default=30)
    parser.add_argument("-min", "--min_ttl", type=int, default=1)
    parser.add_argument("-n", "--num_series", type=int, default=1, help="Number of series per hop")
    parser.add_argument("-p", "--port", type=int, default=33434)
    parser.add_argument("-s", "--size", type=int, default=60, help="Packet size")
    parser.add_argument("-w", "--wait", type=float, default=0.2, help="Wait time between packets")
    parser.add_argument("-t", "--timeout", type=int, default=2)

    args = parser.parse_args()

    #Robust Input Parsing for TXT and CSV
    targets = []
    try:
        with open(args.input_file, "r") as f:
            for line in f:
                # Splits by commas or whitespace to support both CSV and TXT
                parts = line.replace(',', ' ').split()
                for p in parts:
                    clean_ip = p.strip()
                    if clean_ip: targets.append(clean_ip)
    except FileNotFoundError:
        print(f"Error: File {args.input_file} not found.")
        sys.exit(1)

    all_data = {ip: traceroute(ip, args) for ip in targets}

    os.makedirs("data", exist_ok=True)
    with open("data/results.json", "w") as f:
        json.dump(all_data, f, indent=4)
    
    # Raw Text Output
    with open("data/raw_output.txt", "w") as f:
        f.write("INTERNET TOPOLOGY EXPLORER - RAW RESULTS\n")
        f.write("="*40 + "\n")
        for target, hops in all_data.items():
            f.write(f"\nDestination: {target}\n")
            for i, series in enumerate(hops):
                ttl = i + args.min_ttl
                f.write(f"Hop {ttl}:\n")
                for probe in series:
                    # Use .get() to avoid KeyError if the key is missing
                    proto = probe.get('protocol', 'UNKNOWN') 
                    node = f"{probe['ip']} ({probe['name']})" if probe['ip'] else "*"
                    rtt = probe.get('rtt', 0.0)
                    f.write(f"  [{proto}] {node} - RTT: {rtt}ms\n")
    
    print(f"\nData saved to data/results.json and data/raw_output.txt")

    #Automate the Topology Generation
    try:
        from generate_viz import process_for_viz
        process_for_viz("data/results.json", "data/topology.json")
        print("Successfully generated topology.json for visualizer.")
    except ImportError:
        print("Note: generate_viz.py not found. Run it manually to update the UI.")