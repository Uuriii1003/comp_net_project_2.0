import subprocess
import sys
import json
import os
import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from streamlit_agraph import agraph, Node, Edge, Config

PROTO_COLORS = {"UDP": "#1C83E1", "TCP": "#FF4B4B", "ICMP": "#00D166"}
HOME_LAT, HOME_LON = 31.22, 121.48

# --- 1. CORE UTILITIES ---
def get_hop_metrics(h_series):
    if not h_series: return 0.0, 0.0
    timeouts = sum(1 for p in h_series if not p.get("ip"))
    loss = round((timeouts / len(h_series)) * 100, 1)
    rtts = [p["rtt"] for p in h_series if p.get("ip")]
    avg_rtt = round(sum(rtts)/len(rtts), 2) if rtts else 0.0
    return loss, avg_rtt

def generate_raw_report(target_ip, hops):
    report = f"TRACEROUTE REPORT: {target_ip}\n" + "="*40 + "\n"
    for i, h_series in enumerate(hops):
        report += f"Hop {i+1}:\n"
        for p in h_series:
            node = f"{p['ip']} ({p['name']})" if p['ip'] else "*"
            report += f"  [{p['protocol']}] {node:30} - {p['rtt']}ms\n"
    return report

st.set_page_config(layout="wide", page_title="Internet Topology Explorer")

if 'current_data' not in st.session_state:
    st.session_state.current_data = None

st.title("🛰️ Internet Topology Explorer")

# --- 2. SIDEBAR: ALL 6 INPUT ARGUMENTS ---
with st.sidebar:
    st.header("Step 1: Input Target")
    single_ip = st.text_input("Single IP address", placeholder="8.8.8.8")
    target_file = st.file_uploader("Batch upload targets.txt", type=["txt", "csv"])

    st.divider()
    st.markdown("### 🎨 Protocol Legend")
    l_col1, l_col2, l_col3 = st.columns(3)
    l_col1.markdown(f"<p style='color:{PROTO_COLORS['UDP']}'>● UDP</p>", unsafe_allow_html=True)
    l_col2.markdown(f"<p style='color:{PROTO_COLORS['TCP']}'>● TCP</p>", unsafe_allow_html=True)
    l_col3.markdown(f"<p style='color:{PROTO_COLORS['ICMP']}'>● ICMP</p>", unsafe_allow_html=True)
    st.divider()
    st.header("Step 2: Customize Arguments")
    col1, col2 = st.columns(2)
    with col1:
        min_ttl = st.number_input("Min TTL", 1, 30, 1)
        num_series = st.number_input("Series/Hop", 1, 10, 1)
        pkt_size = st.number_input("Packet Size", 28, 1400, 60)
    with col2:
        max_ttl = st.number_input("Max TTL", 1, 60, 20)
        timeout = st.number_input("Timeout (s)", 1, 10, 1)
        wait_time = st.number_input("Wait (s)", 0.0, 5.0, 0.2)
    
    run_btn = st.button("🚀 Launch Traceroute", type="primary", use_container_width=True)

# --- 3. EXECUTION ---
if run_btn:
    st.session_state.current_data = None 
    tmp_path = "targets_current.txt"
    with open(tmp_path, "w") as f:
        if single_ip.strip(): f.write(single_ip.strip())
        elif target_file: f.write(target_file.read().decode())

    cmd = ["sudo", sys.executable, "src/main.py", tmp_path, "-min", str(min_ttl), "-m", str(max_ttl), 
           "-n", str(num_series), "-s", str(pkt_size), "-t", str(timeout), "-w", str(wait_time)]
    
    # Estimate max possible runtime and set a hard timeout to prevent UI from hanging
    max_subprocess_timeout = int(max_ttl) * int(num_series) * 3 * (int(timeout) + float(wait_time)) + 30
    with st.spinner("Probing Internet Topology..."):
        try:
            subprocess.run(cmd, timeout=max_subprocess_timeout)
        except subprocess.TimeoutExpired:
            st.warning("Traceroute timed out. Partial results may be available.")
    
    if os.path.exists("data/results.json"):
        with open("data/results.json", "r") as f: 
            st.session_state.current_data = json.load(f)
    st.rerun()

# --- 4. DATA VISUALIZATION WITH SEARCHBAR ---
if st.session_state.current_data:
    # --- SEARCHBAR IMPLEMENTATION ---
    search_query = st.text_input("🔍 Search results by IP or Hostname...", placeholder="e.g. 1.1.1.1").strip().lower()
    
    # Filter targets based on search
    filtered_targets = {
        ip: hops for ip, hops in st.session_state.current_data.items() 
        if search_query in ip.lower() or any(search_query in str(p.get('name', '')).lower() for h in hops for p in h)
    }

    if not filtered_targets:
        st.warning(f"No results found matching '{search_query}'")
    
    for target_ip, hops in filtered_targets.items():
        with st.expander(f"📍 Analysis for Target: {target_ip}", expanded=True):
            t1, t2, t3 = st.tabs(["🌍 Geographic Map", "🕸️ Logical Topology", "📊 Data & Logs"])
            
            with t1:
                m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB dark_matter")
                path_coords = [[HOME_LAT, HOME_LON]]
                
                for i, h_series in enumerate(hops):
                    p = next((p for p in h_series if p.get('geo') and p['geo'].get('lat') is not None), None)
                    if p:
                        h_loss, h_avg_rtt = get_hop_metrics(h_series)
                        pos = [p['geo']['lat'], p['geo']['lon']]
                        path_coords.append(pos)
                        
                        hover_html = f"""
                        <div style="font-family:sans-serif; font-size:12px; width:200px; color:white; background-color:#1E1E1E; padding:12px; border:1px solid #00f2ff; border-radius:8px;">
                            <b style="color:#00f2ff; font-size:14px;">HOP {i+1}</b><br>
                            <hr style="border:0; border-top:1px solid #444; margin:8px 0;">
                            <b>1. Hostname:</b> {p.get('name', 'Unknown')}<br>
                            <b>2. IP Address:</b> {p.get('ip', '*')}<br>
                            <b>3. Protocol:</b> {p.get('protocol')}<br>
                            <b>4. Current RTT:</b> {p.get('rtt')} ms<br>
                            <b>5. Avg Hop RTT:</b> {h_avg_rtt} ms<br>
                            <b>6. Hop Loss Rate:</b> {h_loss}%
                        </div>
                        """
                        folium.CircleMarker(
                            location=pos, radius=8, color="white", weight=2, fill=True,
                            fill_color=PROTO_COLORS.get(p['protocol'], "#00f2ff"), fill_opacity=1,
                            tooltip=folium.Tooltip(hover_html, sticky=True)
                        ).add_to(m)

                if len(path_coords) > 1:
                    folium.PolyLine(path_coords, color="#00f2ff", weight=2, opacity=0.4).add_to(m)
                    m.fit_bounds(path_coords)
                st_folium(m, width=None, height=500, key=f"map_{target_ip}")

            with t2:
                nodes, edges = [], []
                root_id = f"root_{target_ip}"
                nodes.append(Node(id=root_id, label="SOURCE", color="#FFFFFF", size=25))
                prev_id = root_id
                for i, h_series in enumerate(hops):
                    valid_p = next((p for p in h_series if p.get("ip")), None)
                    if valid_p:
                        curr_id = f"{target_ip}_h{i}_{valid_p['ip']}"
                        thickness = max(2, 12 - (valid_p['rtt'] / 20))
                        nodes.append(Node(id=curr_id, label=f"H{i+1}: {valid_p['ip']}", color=PROTO_COLORS.get(valid_p['protocol'])))
                        edges.append(Edge(source=prev_id, target=curr_id, label=f"{valid_p['rtt']}ms", color=PROTO_COLORS.get(valid_p['protocol']), width=thickness))
                        prev_id = curr_id
                with st.container():
                    agraph(nodes=nodes, edges=edges, config=Config(width=1000, height=550, directed=True, physics=True))

            with t3:
                loss_data = []
                for i, h_series in enumerate(hops):
                    l, r = get_hop_metrics(h_series)
                    p_main = next((p for p in h_series if p['ip']), h_series[0])
                    loss_data.append({"Hop": i+1, "Hostname": p_main.get('name'), "IP": p_main.get('ip'), "Proto": p_main.get('protocol'), "Avg RTT": r, "Loss %": l})
                st.table(pd.DataFrame(loss_data))
                st.download_button("💾 Download Results", generate_raw_report(target_ip, hops), f"report_{target_ip}.txt", key=f"dl_{target_ip}")
else:
    st.info("Launch a traceroute to view analysis.")