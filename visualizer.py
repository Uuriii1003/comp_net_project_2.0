import subprocess
import sys
import json
import os
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import AntPath
import time

# --- 1. CORE LOGIC: RAW OUTPUT GENERATOR ---
def generate_raw_from_topology(topo_data):
    """Generates a CLI-style text block matching your raw output screenshots."""
    nodes = {n['id']: n for n in topo_data['nodes']}
    links = topo_data['links']
    dest = topo_data['nodes'][-1]['id']
    output = f"traceroute to {dest} ({dest}), 30 hops max, 60 byte packets\n"
    
    for i, link in enumerate(links):
        hop_num = i + 1
        target_id = link['target']
        node_info = nodes.get(target_id, {})
        hostname = node_info.get('name', 'Unknown')
        ip = node_info.get('id', '*')
        rtt = link.get('rtt', 0.0)
        
        if ip != "*":
            output += f"{hop_num:2}  {hostname} ({ip})  {rtt} ms  {rtt} ms  {rtt} ms\n"
        else:
            output += f"{hop_num:2}  * * *\n"
    return output

# --- 2. UTILITY: NETWORK METRICS ---
def get_hop_loss(hop_series):
    if not hop_series: return 0
    timeouts = sum(1 for probe in hop_series if not probe.get("ip"))
    return round((timeouts / len(hop_series)) * 100, 1)

st.set_page_config(layout="wide", page_title="Internet Topology Explorer")

# --- 3. UI STATE MANAGEMENT ---
if 'trace_done' not in st.session_state: st.session_state.trace_done = False
if 'active_path' not in st.session_state: st.session_state.active_path = []
if 'map_key' not in st.session_state: st.session_state.map_key = 0
if 'map_center' not in st.session_state: st.session_state.map_center = [20, 0]
if 'map_zoom' not in st.session_state: st.session_state.map_zoom = 2

st.title("🛰️ Internet Topology Explorer")

# --- 4. SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("Step 1: Input Target")
    single_ip = st.text_input("Single IP address", placeholder="e.g. 8.8.8.8")
    target_file = st.file_uploader("Batch upload targets.txt", type=["txt", "csv"])

    st.divider()
    st.header("Step 2: Customize Arguments")
    col1, col2 = st.columns(2)
    with col1:
        min_ttl = st.number_input("Min TTL", 1, 30, 1)
        num_series = st.number_input("Probes/Hop", 1, 10, 3)
        pkt_size = st.number_input("Packet size", 28, 512, 60)
    with col2:
        max_ttl = st.number_input("Max TTL", 1, 60, 20)
        timeout = st.number_input("Timeout (s)", 1, 10, 2)
        port = st.number_input("Dest port", 1, 65535, 33434)
    
    st.divider()
    st.header("Protocol Analysis Filter")
    show_udp = st.checkbox("UDP", value=True)
    show_tcp = st.checkbox("TCP", value=True)
    show_icmp = st.checkbox("ICMP", value=True)
    
    run_btn = st.button("🚀 Launch Traceroute", type="primary", use_container_width=True)

# --- 5. EXECUTION ---
if run_btn:
    st.session_state.trace_done = False
    tmp_path = "targets_current.txt"
    if single_ip.strip():
        with open(tmp_path, "w") as f: f.write(single_ip.strip())
    else:
        with open(tmp_path, "wb") as f: f.write(target_file.read())

    cmd = ["sudo", sys.executable, "main.py", tmp_path, "-min", str(min_ttl), "-m", str(max_ttl),
           "-n", str(num_series), "-p", str(port), "-s", str(pkt_size), "-t", str(timeout)]
    
    bar = st.progress(0)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for i in range(100):
        time.sleep(0.04)
        bar.progress(i + 1)
    proc.wait()
    st.session_state.trace_done = True
    st.rerun()

# --- 6. DATA LOADING ---
data, topo_data = {}, {}
if st.session_state.trace_done:
    if os.path.exists("results.json"):
        with open("results.json", "r") as f: data = json.load(f)
    if os.path.exists("topology.json"):
        with open("topology.json", "r") as f: topo_data = json.load(f)

# # --- 7. MAIN LAYOUT: MAP & ANALYZER ---
# col_map, col_out = st.columns([1.3, 1.2])

# with col_map:
#     st.subheader("Step 4: Interactive Topology Map")
#     m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, tiles="CartoDB dark_matter")
    
#     if st.session_state.active_path:
#         for pt in st.session_state.active_path:
#             folium.CircleMarker(location=pt, radius=5, color="#00f2ff", fill=True).add_to(m)
#         AntPath(locations=st.session_state.active_path, color="#00f2ff", weight=3).add_to(m)

#     st_folium(m, width=None, height=600, use_container_width=True, key=f"map_{st.session_state.map_key}")

# with col_out:
#     st.markdown("<h2 style='text-align:center; color:#00f2ff;'>Trace Results</h2>", unsafe_allow_html=True)
    
#     if data and st.session_state.trace_done:
#         search_query = st.text_input("🔍 Search by IP or Hostname...")
        
#         for target, hops in data.items():
#             if search_query.lower() not in target.lower(): continue
            
#             # Loss Calculation
#             loss_total = get_hop_loss(hops[-1])
            
#             with st.expander(f"🌐 {target} — Loss: {loss_total}%", expanded=True):
                
#                 # Geolocation Error Handling
#                 coords = []
#                 non_viz = 0
#                 for h in hops:
#                     geo = h[0].get('geo', {})
#                     if geo.get('lat'): coords.append([geo['lat'], geo['lon']])
#                     else: non_viz += 1
                
#                 if non_viz > 0:
#                     st.error(f"⚠️ {non_viz} router IPs could not be visualized on the map.")

#                 # Action Buttons
#                 c1, c2 = st.columns(2)
#                 with c1:
#                     if st.button(f"▶️ Play Trace for {target}", key=f"p_{target}"):
#                         st.session_state.active_path = coords
#                         st.session_state.map_key += 1
#                         st.rerun()
#                 with c2:
#                     if topo_data:
#                         raw_txt = generate_raw_from_topology(topo_data)
#                         st.download_button("💾 Download Raw Result", raw_txt, f"trace_{target}.txt", key=f"d_{target}")

#                 # Deep Packet Analysis Table
#                 st.write("**Deep Packet Analysis**")
#                 table = []
#                 for i, h_series in enumerate(hops):
#                     for probe in h_series:
#                         if (show_udp and probe['protocol']=="UDP") or \
#                            (show_tcp and probe['protocol']=="TCP") or \
#                            (show_icmp and probe['protocol']=="ICMP"):
#                             table.append({
#                                 "TTL": i+1, "Protocol": probe['protocol'],
#                                 "Router IP": probe['ip'] if probe['ip'] else "N/A",
#                                 "RTT (ms)": str(probe['rtt']) if probe['ip'] else "timeout"
#                             })
#                 st.dataframe(table, use_container_width=True, height=350)
#     else:
#         st.info("Awaiting trace data...")

# --- 7. MAIN LAYOUT: MAP & ANALYZER ---
col_map, col_out = st.columns([1.5, 1])

# Set your "Home" anchor (e.g., Shanghai NYU)
HOME_LAT, HOME_LON = 31.22, 121.48 

with col_map:
    st.subheader("🌐 Global Path Tree")
    m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB dark_matter")
    
    all_coords = []

    if data:
        for target, hops in data.items():
            # 1. DATA EXTRACTION: Find the best geo data for each hop
            path_info = []
            for h_series in hops:
                # Optimized search: check all probes in a hop for coordinates
                best_probe = next((p for p in h_series if p.get('geo', {}).get('lat')), h_series[0])
                geo = best_probe.get('geo', {})
                path_info.append({
                    "lat": geo.get('lat'), 
                    "lon": geo.get('lon'), 
                    "ip": best_probe.get('ip', '*'),
                    "proto": best_probe.get('protocol', 'UDP'),
                    "name": best_probe.get('name', 'Unknown')
                })

            # 2. LINEAR INTERPOLATION: Calculate coordinates for every hop (Straight Line Logic)
            final_coords = []
            last_known_pos = [HOME_LAT, HOME_LON]
            last_known_idx = -1

            for i in range(len(path_info)):
                next_known_pos = None
                next_known_idx = -1
                for j in range(i, len(path_info)):
                    if path_info[j]['lat'] is not None:
                        next_known_idx = j
                        next_known_pos = [path_info[j]['lat'], path_info[j]['lon']]
                        break
                
                if path_info[i]['lat'] is not None:
                    pos = [path_info[i]['lat'], path_info[i]['lon']]
                    final_coords.append(pos)
                    last_known_pos, last_known_idx = pos, i
                elif next_known_pos:
                    steps = next_known_idx - last_known_idx
                    current_step = i - last_known_idx
                    lat = last_known_pos[0] + (next_known_pos[0] - last_known_pos[0]) * (current_step / steps)
                    lon = last_known_pos[1] + (next_known_pos[1] - last_known_pos[1]) * (current_step / steps)
                    final_coords.append([lat, lon])
                else:
                    # Trailing hops: offset slightly from the last known spot
                    pos = [last_known_pos[0] + 0.5, last_known_pos[1] + 0.5]
                    final_coords.append(pos)
                    last_known_pos = pos

            # 3. DRAWING: Use protocol colors for the line and markers
            colors = {"UDP": "#3498db", "TCP": "#e74c3c", "ICMP": "#2ecc71"}
            main_color = colors.get(path_info[0]['proto'], "#00f2ff")

            folium.PolyLine(final_coords, color=main_color, weight=4, opacity=0.8).add_to(m)
            
            for idx, coord in enumerate(final_coords):
                p = path_info[idx]
                label = f"Hop {idx+1}<br>IP: {p['ip']}<br>Host: {p['name']}"
                folium.CircleMarker(
                    location=coord,
                    radius=5,
                    color="white",
                    fill=True,
                    fill_color=main_color,
                    fill_opacity=0.9,
                    popup=folium.Popup(label, max_width=200)
                ).add_to(m)
            
            all_coords.extend(final_coords)

        if all_coords:
            m.fit_bounds(all_coords)

    st_folium(m, width=None, height=650, use_container_width=True, key="topology_map")

with col_out:
    st.markdown("<h2 style='text-align:center; color:#00f2ff;'>Trace Analysis</h2>", unsafe_allow_html=True)
    
    if data:
        # Merge: Teammate's Search bar
        search_query = st.text_input("🔍 Search by IP or Hostname...")
        
        for target, hops in data.items():
            if search_query.lower() not in target.lower(): continue
            
            # Merge: Teammate's Loss Calculation
            loss_total = get_hop_loss(hops[-1])
            
            with st.expander(f"🌐 {target} — Loss: {loss_total}%", expanded=True):
                
                # Merge: Teammate's Download Button (keeping her logic, removing play button)
                if topo_data:
                    raw_txt = generate_raw_from_topology(topo_data)
                    st.download_button("💾 Download Raw Result", raw_txt, f"trace_{target}.txt", key=f"d_{target}")

                # Merge: Teammate's Deep Packet Analysis Table
                st.write("**Deep Packet Analysis**")
                table = []
                for i, h_series in enumerate(hops):
                    for probe in h_series:
                        # Check against protocol filters from the sidebar
                        if (show_udp and probe['protocol']=="UDP") or \
                           (show_tcp and probe['protocol']=="TCP") or \
                           (show_icmp and probe['protocol']=="ICMP"):
                            table.append({
                                "TTL": i+1, 
                                "Protocol": probe['protocol'],
                                "Router IP": probe['ip'] if probe['ip'] else "N/A",
                                "RTT (ms)": probe['rtt'] if probe['ip'] else "timeout"
                            })
                st.dataframe(table, use_container_width=True, height=400)
    else:
        st.info("Awaiting trace data...")