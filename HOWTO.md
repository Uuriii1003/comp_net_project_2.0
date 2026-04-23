🛰️ Internet Topology Explorer
A professional-grade network analysis tool that combines multi-protocol traceroute capabilities with geographic and logical visualization.

📂 Source Code Structure
Based on our project directory, the system is organized as follows:

⚙️ Core Logic (src/)

src/main.py: The backend orchestration script that handles CLI arguments and coordinates the probing logic.

src/packets.py: Core networking layer using Scapy to generate multi-protocol (ICMP/TCP/UDP) traceroute packets.

src/parser.py: Extracts metadata from network responses and integrates geographic data.

src/generate_viz.py: Helper utility for static visualization rendering.

🖥️ Frontend & Data

visualizer.py: The primary Streamlit frontend. It handles the search interface, input parameters, and the 3-segment visualization dashboard.

data/: Directory containing data exchange files (results.json, topology.json) and target lists (targets.txt).

✨ Key Design Choices
Logical Performance Weighting: In the "Logical Topology" view, the link thickness between nodes is dynamically scaled based on RTT. Thicker lines indicate lower latency (higher performance).

Protocol Color Coding: Nodes and edges are colored by protocol for immediate identification:

UDP: Blue 🔵

TCP: Red 🔴

ICMP: Green 🟢

Searchable Analysis: Includes a global search bar to filter through massive batch results by IP or Hostname.

🚀 Getting Started
For detailed installation steps, system requirements, and operational instructions, please refer to the dedicated guide:

👉 View the Installation & Operation Guide (HOWTO.md)

🧹 Maintenance
To clear temporary JSON data, targets, and Python cache:

Bash
make clean
[!NOTE]

This project requires Sudo/Root Privileges for Scapy raw packet injection.