import json

def process_for_viz(input_filename, output_filename):
    with open(input_filename, 'r') as f:
        raw_data = json.load(f)

    nodes = {}
    links = []

    # Add Source Node
    nodes["localhost"] = {"id": "localhost", "name": "My Computer", "group": 1}

    for target_ip, hops in raw_data.items():
        previous_node_id = "localhost"
        
        for hop_index, series in enumerate(hops):
            # Find the first successful response in this hop to represent the node
            valid_probe = next((p for p in series if p["ip"]), None)
            
            if valid_probe:
                current_id = valid_probe["ip"]
                if current_id not in nodes:
                    nodes[current_id] = {
                        "id": current_id,
                        "name": valid_probe["name"],
                        "lat": valid_probe["geo"].get("lat"),
                        "lon": valid_probe["geo"].get("lon"),
                        "city": valid_probe["geo"].get("city"),
                        "group": 2 if not valid_probe["is_destination"] else 3
                    }
                
                # Create a link from the previous hop to this one
                # We use the protocol of the first successful probe for the link color
                links.append({
                    "source": previous_node_id,
                    "target": current_id,
                    "protocol": valid_probe["protocol"],
                    "rtt": valid_probe["rtt"]
                })
                previous_node_id = current_id

    with open(output_filename, 'w') as f:
        json.dump({"nodes": list(nodes.values()), "links": links}, f, indent=4)

if __name__ == "__main__":
    process_for_viz("data/results.json", "data/topology.json")