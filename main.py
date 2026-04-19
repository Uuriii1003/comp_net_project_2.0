# import time
# import json
# import argparse
# import os
# import sys
# from scapy.all import sr1
# from packets import create_probe
# from parser import send_and_parse

# def traceroute(target_ip, args):
#     results = []
#     print(f"\n--- Tracing {target_ip} (Max TTL: {args.max_ttl}) ---")

#     for ttl in range(args.min_ttl, args.max_ttl + 1):
#         ttl_results = []
#         reached_destination = False

#         # Every hop sends UDP, TCP, and ICMP
#         for _ in range(args.num_series):
#             for protocol in ["UDP", "TCP", "ICMP"]:
#                 packet = create_probe(target_ip, ttl, protocol, args.port, args.size)
                
#                 start = time.perf_counter()
#                 response = sr1(packet, timeout=args.timeout, verbose=0)
#                 end = time.perf_counter()
                
#                 result = send_and_parse(response, protocol, (end - start) * 1000, ttl, target_ip)
#                 ttl_results.append(result)

#                 # Live Output formatting
#                 status = f"{result['ip']} ({result['name']})" if result['ip'] else "*"
#                 print(f"TTL {ttl} | {protocol}: {status} - {result['rtt']}ms")

#                 if result["is_destination"]:
#                     reached_destination = True

#                 time.sleep(args.wait)

#         results.append(ttl_results)
#         if reached_destination:
#             print(f"✅ Reached {target_ip}")
#             break
#     return results

# if __name__ == "__main__":
#     if os.geteuid() != 0:
#         print("Error: Run with 'sudo'")
#         sys.exit(1)

#     parser = argparse.ArgumentParser(description="Internet Topology Explorer")
#     parser.add_argument("input_file", help="TXT file containing list of IPs")
#     parser.add_argument("-m", "--max_ttl", type=int, default=30)
#     parser.add_argument("-min", "--min_ttl", type=int, default=1)
#     parser.add_argument("-n", "--num_series", type=int, default=1, help="Number of series per hop")
#     parser.add_argument("-p", "--port", type=int, default=33434)
#     parser.add_argument("-s", "--size", type=int, default=60, help="Packet size")
#     parser.add_argument("-w", "--wait", type=float, default=0.2, help="Wait time between packets")
#     parser.add_argument("-t", "--timeout", type=int, default=2)

#     args = parser.parse_args()

#     # Load targets from file
#     with open(args.input_file, "r") as f:
#         targets = [line.strip() for line in f if line.strip()]

#     all_data = {ip: traceroute(ip, args) for ip in targets}

#     # Save results to JSON for the Visualizer
#     with open("results.json", "w") as f:
#         json.dump(all_data, f, indent=4)
#     print(f"\nResults saved to results.json")



import time
import json
import argparse
import os
import sys
import requests  # New: Required for geographic mapping
from scapy.all import sr1
from packets import create_probe
from parser import send_and_parse

# 🌍 Function to get geographic coordinates for the Map UI
def get_geo_data(ip):
    """Fetches Lat/Long for an IP to place it on the world map."""
    if not ip or ip == "*":
        return {"lat": None, "lon": None, "city": "Unknown"}
    try:
        # Using a free GeoIP API (ip-api.com)
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

        # Requirement: Send three probe packets per series
        for _ in range(args.num_series):
            for protocol in ["UDP", "TCP", "ICMP"]:
                packet = create_probe(target_ip, ttl, protocol, args.port, args.size)
                
                start = time.perf_counter()
                response = sr1(packet, timeout=args.timeout, verbose=0)
                end = time.perf_counter()
                
                result = send_and_parse(response, protocol, (end - start) * 1000, ttl, target_ip)
                
                # 📍 Add Geolocation data for the World Map interface
                if result["ip"]:
                    result["geo"] = get_geo_data(result["ip"])
                else:
                    result["geo"] = {"lat": None, "lon": None, "city": "Unknown"}

                ttl_results.append(result)

                status = f"{result['ip']} ({result['name']})" if result['ip'] else "*"
                print(f"TTL {ttl} | {protocol}: {status} - {result['rtt']}ms")

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
        print("Error: Run with 'sudo'")
        sys.exit(1)

    # These arguments are vital for project compliance
    parser = argparse.ArgumentParser(description="Internet Topology Explorer")
    parser.add_argument("input_file", help="TXT file containing list of IPs")
    parser.add_argument("-m", "--max_ttl", type=int, default=30)
    parser.add_argument("-min", "--min_ttl", type=int, default=1)
    parser.add_argument("-n", "--num_series", type=int, default=1, help="Number of series per hop")
    parser.add_argument("-p", "--port", type=int, default=33434)
    parser.add_argument("-s", "--size", type=int, default=60, help="Packet size")
    parser.add_argument("-w", "--wait", type=float, default=0.2, help="Wait time between packets")
    parser.add_argument("-t", "--timeout", type=int, default=2)

    args = parser.parse_args()

    with open(args.input_file, "r") as f:
        targets = [line.strip() for line in f if line.strip()]

    all_data = {ip: traceroute(ip, args) for ip in targets}

    # Save results to JSON: includes IP, Name, RTT, Protocol, and GeoData
    with open("results.json", "w") as f:
        json.dump(all_data, f, indent=4)
    print(f"\nResults saved to results.json")

    try:
        from generate_viz import process_for_viz
        process_for_viz("results.json", "topology.json")
        print("Topology graph updated successfully.")
    except ImportError:
        print("Could not find generate_viz.py, skipping graph update.")