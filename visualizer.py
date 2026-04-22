import subprocess
import sys
import json
import os
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import AntPath
import time
from streamlit_agraph import agraph, Node, Edge, Config

# --- 1. CORE LOGIC: RAW OUTPUT GENERATOR ---
def generate_raw_from_topology(topo_data):
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
        timeout = st.number_input("Timeout (s)", 1, 10, 1) # Defaulted to 1 for speed
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
    elif target_file:
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

# --- 7. MAIN LAYOUT ---
col_viz, col_out = st.columns([1.5, 1])
HOME_LAT, HOME_LON = 31.22, 121.48 

with col_viz:
    view_mode = st.radio("Select View:", ["Geographic Map", "Logical Topology"], horizontal=True, label_visibility="collapsed")

    if view_mode == "Geographic Map":
        st.subheader("🌐 Global Path Tree")
        m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB dark_matter")
        all_coords = []

        if data:
            for target, hops in data.items():
                path_info = []
                for h_series in hops:
                    timeouts = sum(1 for p in h_series if not p.get('ip'))
                    loss_rate = round((timeouts / len(h_series)) * 100, 1)
                    best_p = next((p for p in h_series if p.get('geo', {}).get('lat')), h_series[0])
                    geo = best_p.get('geo', {})
                    path_info.append({
                        "lat": geo.get('lat'), "lon": geo.get('lon'), 
                        "ip": best_p.get('ip', '*'), "proto": best_p.get('protocol', 'UDP'),
                        "name": best_p.get('name', 'Unknown'), "rtt": best_p.get('rtt', 0.0),
                        "loss": loss_rate
                    })

                # --- LINEAR INTERPOLATION ---
                final_coords = []
                last_known_pos, last_known_idx = [HOME_LAT, HOME_LON], -1

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
                        steps_in_gap = next_k_idx - last_known_idx
                        current_step = i - last_known_idx
                        progress = current_step / steps_in_gap
                        lat = last_known_pos[0] + (next_k_pos[0] - last_known_pos[0]) * progress
                        lon = last_known_pos[1] + (next_k_pos[1] - last_known_pos[1]) * progress
                        final_coords.append([lat, lon])
                    else:
                        pos = [last_known_pos[0] + 0.1, last_known_pos[1] + 0.1]
                        final_coords.append(pos)
                        last_known_pos = pos

                proto_colors = {"TCP": "#FF4B4B", "UDP": "#1C83E1", "ICMP": "#00D166"}
                
                # Link Drawing
                for idx in range(len(final_coords) - 1):
                    seg_color = proto_colors.get(path_info[idx+1]['proto'], "#00f2ff")
                    folium.PolyLine([final_coords[idx], final_coords[idx+1]], color=seg_color, weight=4, opacity=0.8).add_to(m)
                
                # Marker Drawing with RESTORED HOVER INFO
                for idx, coord in enumerate(final_coords):
                    p = path_info[idx]
                    hover_html = f"""
                        <div style="font-family: sans-serif; font-size: 12px;">
                            <b>Hop {idx+1}</b><br>
                            <b>IP:</b> {p['ip']}<br>
                            <b>Host:</b> {p['name']}<br>
                            <b>Protocol:</b> {p['proto']}<br>
                            <b>RTT:</b> {p['rtt']}ms<br>
                            <b>Loss:</b> {p['loss']}%
                        </div>
                    """
                    folium.CircleMarker(
                        location=coord, 
                        radius=6, 
                        color="white", 
                        fill=True, 
                        fill_color=proto_colors.get(p['proto'], "#00f2ff"),
                        tooltip=folium.Tooltip(hover_html)
                    ).add_to(m)
                all_coords.extend(final_coords)
            if all_coords: m.fit_bounds(all_coords)
        st_folium(m, width=None, height=650, use_container_width=True, key="geo_map")

    else:
        st.subheader("🕸️ Logical Network Graph")
        if topo_data:
            nodes, edges = [], []
            for n in topo_data['nodes']:
                # Dynamic coloring based on role
                color = "#1C83E1" if n == topo_data['nodes'][0] else ("#FF4B4B" if n == topo_data['nodes'][-1] else "#00f2ff")
                nodes.append(Node(id=n['id'], label=n.get('name', n['id']), color=color, size=15))
            for l in topo_data['links']:
                edges.append(Edge(source=l['source'], target=l['target'], label=f"{l.get('rtt')}ms"))
            
            config = Config(width=800, height=600, directed=True, physics=True, hierarchical=False)
            agraph(nodes=nodes, edges=edges, config=config)

# --- 8. ANALYZER PANEL ---
with col_out:
    st.markdown("<h2 style='text-align:center; color:#00f2ff;'>Trace Analysis</h2>", unsafe_allow_html=True)
    if data:
        search = st.text_input("🔍 Search IP/Host...")
        for target, hops in data.items():
            if search.lower() not in target.lower(): continue
            with st.expander(f"🌐 {target} — Loss: {get_hop_loss(hops[-1])}%", expanded=True):
                if topo_data:
                    st.download_button("💾 Download CLI Log", generate_raw_from_topology(topo_data), f"trace_{target}.txt", key=f"d_{target}")
                
                table = []
                for i, h_series in enumerate(hops):
                    for probe in h_series:
                        if (show_udp and probe['protocol']=="UDP") or \
                           (show_tcp and probe['protocol']=="TCP") or \
                           (show_icmp and probe['protocol']=="ICMP"):
                            table.append({
                                "TTL": i+1, 
                                "Proto": probe['protocol'], 
                                "IP": probe['ip'] or "N/A", 
                                "RTT": f"{probe['rtt']}ms" if probe['ip'] else "timeout"
                            })
                st.dataframe(table, use_container_width=True, height=400)