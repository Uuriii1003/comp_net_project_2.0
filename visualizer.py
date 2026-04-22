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

# Set your "Home" anchor
HOME_LAT, HOME_LON = 31.22, 121.48 

with col_map:
    st.subheader("🌐 Global Path Tree")
    m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB dark_matter")
    
    all_coords = []

    if data:
        for target, hops in data.items():
            # 1. DATA EXTRACTION
            path_info = []
            for h_series in hops:
                timeouts = sum(1 for p in h_series if not p.get('ip'))
                loss_rate = round((timeouts / len(h_series)) * 100, 1)
                
                # Get best geo data available in the hop
                best_p = next((p for p in h_series if p.get('geo', {}).get('lat')), h_series[0])
                geo = best_p.get('geo', {})
                
                path_info.append({
                    "lat": geo.get('lat'), "lon": geo.get('lon'), 
                    "ip": best_p.get('ip', '*'), "proto": best_p.get('protocol', 'UDP'),
                    "name": best_p.get('name', 'Unknown'), "rtt": best_p.get('rtt', 0.0),
                    "loss": loss_rate
                })

            # 2. SIMPLE LINEAR INTERPOLATION (No zigzag, even spacing)
            final_coords = []
            last_known_pos = [HOME_LAT, HOME_LON]
            last_known_idx = -1

            for i in range(len(path_info)):
                next_k_pos, next_k_idx = None, -1
                for j in range(i, len(path_info)):
                    if path_info[j]['lat'] is not None:
                        next_k_idx, next_k_pos = j, [path_info[j]['lat'], path_info[j]['lon']]
                        break
                
                if path_info[i]['lat'] is not None:
                    pos = [path_info[i]['lat'], path_info[i]['lon']]
                    final_coords.append(pos)
                    last_known_pos, last_known_idx = pos, i
                elif next_k_pos:
                    # Even spacing: (current hop index - start) / (total hops in gap)
                    steps_in_gap = next_k_idx - last_known_idx
                    current_step = i - last_known_idx
                    progress = current_step / steps_in_gap
                    
                    lat = last_known_pos[0] + (next_k_pos[0] - last_known_pos[0]) * progress
                    lon = last_known_pos[1] + (next_k_pos[1] - last_known_pos[1]) * progress
                    final_coords.append([lat, lon])
                else:
                    # Trailing hops: simple small offset
                    pos = [last_known_pos[0] + 0.1, last_known_pos[1] + 0.1]
                    final_coords.append(pos)
                    last_known_pos = pos

            # 3. DRAWING ENGINE
            proto_colors = {"TCP": "#FF4B4B", "UDP": "#1C83E1", "ICMP": "#00D166"}
            
            # Draw Links with Protocol Colors per segment
            for idx in range(len(final_coords) - 1):
                segment = [final_coords[idx], final_coords[idx+1]]
                segment_proto = path_info[idx+1]['proto']
                seg_color = proto_colors.get(segment_proto, "#00f2ff")
                
                folium.PolyLine(
                    segment, color=seg_color, weight=4, opacity=0.8,
                    tooltip=f"Link Protocol: {segment_proto}"
                ).add_to(m)
            
            # Draw Node Markers with Hover Info
            for idx, coord in enumerate(final_coords):
                p = path_info[idx]
                node_color = proto_colors.get(p['proto'], "#00f2ff")
                
                hover_text = f"""
                    <b>Hop {idx+1}</b><br>
                    IP: {p['ip']}<br>
                    Host: {p['name']}<br>
                    Protocol: {p['proto']}<br>
                    RTT: {p['rtt']} ms<br>
                    Loss Rate: {p['loss']}%
                """
                
                folium.CircleMarker(
                    location=coord, radius=5, color="white", fill=True,
                    fill_color=node_color, fill_opacity=0.9,
                    tooltip=folium.Tooltip(hover_text)
                ).add_to(m)
            
            all_coords.extend(final_coords)

        if all_coords:
            m.fit_bounds(all_coords)

    st_folium(m, width=None, height=650, use_container_width=True, key="topology_map")

with col_out:
    st.markdown("<h2 style='text-align:center; color:#00f2ff;'>Trace Analysis</h2>", unsafe_allow_html=True)
    if data:
        search_query = st.text_input("🔍 Search by IP or Hostname...")
        for target, hops in data.items():
            if search_query.lower() not in target.lower(): continue
            loss_total = get_hop_loss(hops[-1])
            with st.expander(f"🌐 {target} — Loss: {loss_total}%", expanded=True):
                if topo_data:
                    raw_txt = generate_raw_from_topology(topo_data)
                    st.download_button("💾 Download", raw_txt, f"trace_{target}.txt", key=f"d_{target}")
                
                table = []
                for i, h_series in enumerate(hops):
                    for probe in h_series:
                        if (show_udp and probe['protocol']=="UDP") or \
                           (show_tcp and probe['protocol']=="TCP") or \
                           (show_icmp and probe['protocol']=="ICMP"):
                            table.append({
                                "TTL": i+1, "Protocol": probe['protocol'],
                                "Router IP": probe['ip'] if probe['ip'] else "N/A",
                                "RTT (ms)": probe['rtt'] if probe['ip'] else "timeout"
                            })
                st.dataframe(table, use_container_width=True, height=400)
    else:
        st.info("Awaiting trace data...")