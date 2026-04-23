# 🛰️ Internet Topology Explorer

A professional-grade network analysis tool that combines multi-protocol traceroute capabilities with geographic and logical visualization.

## Source Code Structure
Based on our project directory, the system is organized as follows:
- **visualizer.py**: The primary Streamlit frontend. It handles the search interface, input parameters, and the 3-segment visualization dashboard.
- **main.py**: The backend orchestration script that handles CLI arguments and coordinates the probing logic.
- **packets.py**: Core networking layer using Scapy to generate multi-protocol (ICMP/TCP/UDP) traceroute packets.
- **parser.py**: Extracts metadata from network responses and integrates geographic data.
- **generate_viz.py**: Helper utility for static visualization rendering.
- **results.json / topology.json**: Data exchange files used to pass results between the backend and frontend.
- **targets.txt**: Default input file for batch processing multiple IP addresses.

## Key Design Choices
- **Logical Performance Weighting**: In the "Logical Topology" view, the link thickness between nodes is dynamically scaled based on RTT. Thicker lines indicate lower latency (higher performance).
- **Protocol Color Coding**: Nodes and edges are colored by protocol (UDP: Blue, TCP: Red, ICMP: Green) for immediate identification.
- **Searchable Analysis**: Includes a global search bar to filter through massive batch results by IP or Hostname.
