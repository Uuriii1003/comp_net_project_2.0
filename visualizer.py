import subprocess
import sys
import json
import os
import ipaddress
import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="Internet Topology Explorer")
st.title("Internet Topology Explorer")

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Target")

    # Single IP input (from index.html)
    single_ip = st.text_input("Single IP address", placeholder="e.g. 8.8.8.8")

    st.markdown("<div style='text-align:center;color:gray;margin:4px 0'>— OR —</div>", unsafe_allow_html=True)

    # Batch file upload
    target_file = st.file_uploader("Batch upload targets.txt", type=["txt"])

    st.divider()
    st.header("Traceroute Options")

    col1, col2 = st.columns(2)
    with col1:
        min_ttl    = st.number_input("Min TTL",      min_value=1,  max_value=30,  value=1)
        num_series = st.number_input("Series/Hop",   min_value=1,  max_value=5,   value=1,
                                     help="Number of probe rounds per hop")
        pkt_size   = st.number_input("Packet size",  min_value=28, max_value=512, value=60,
                                     help="Total IP payload bytes")
    with col2:
        max_ttl    = st.number_input("Max TTL",      min_value=1,  max_value=60,  value=30)
        timeout    = st.number_input("Timeout (s)",  min_value=1,  max_value=10,  value=2)
        port       = st.number_input("Dest port",    min_value=1,  max_value=65535, value=33434)

    wait = st.slider("Wait between packets (s)", min_value=0.0, max_value=2.0,
                     value=0.2, step=0.1)

    st.divider()

    run_btn = st.button("Start Traceroute", type="primary", use_container_width=True)

    # ── RUN LOGIC ────────────────────────────────────────────────────────────
    if run_btn:
        # Validate: need either a single IP or a file
        if not single_ip.strip() and target_file is None:
            st.error("Enter an IP address or upload a targets.txt file.")
            st.stop()

        # If single IP typed, validate it and write a temp file
        if single_ip.strip():
            try:
                ipaddress.ip_address(single_ip.strip())
            except ValueError:
                st.error(f"'{single_ip.strip()}' is not a valid IP address.")
                st.stop()
            tmp_path = "/tmp/targets_single.txt"
            with open(tmp_path, "w") as f:
                f.write(single_ip.strip() + "\n")

        # If file uploaded, save it to disk
        if target_file is not None:
            tmp_path = "/tmp/targets_uploaded.txt"
            with open(tmp_path, "wb") as f:
                f.write(target_file.read())

        cmd = [
            "sudo", sys.executable, "main.py", tmp_path,
<<<<<<< HEAD
            "--min_ttl",    str(min_ttl),
            "--max_ttl",    str(max_ttl),
            "--num_series", str(num_series),
            "--port",       str(port),
            "--size",       str(pkt_size),
            "--wait",       str(wait),
            "--timeout",    str(timeout),
=======
            "-min",    str(min_ttl),
            "-m",    str(max_ttl),
            "-n", str(num_series),
            "-p",       str(port),
            "-s",       str(pkt_size),
            "-s",       str(wait),
            "-t",    str(timeout),
>>>>>>> bb4e9cd (updated visualizer)
        ]

        st.info("Running traceroute — this may take a minute...")
        log_area  = st.empty()
        log_lines = []

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            for line in proc.stdout:
                log_lines.append(line.rstrip())
                log_area.code("\n".join(log_lines), language="text")
            proc.wait()

            if proc.returncode == 0:
                # Regenerate topology.json automatically
                try:
                    from generate_viz import process_for_viz
                    process_for_viz("results.json", "topology.json")
                except Exception as e:
                    st.warning(f"topology.json not updated: {e}")
                st.success("Done! Map updated below.")
                st.rerun()
            else:
                st.error(f"main.py exited with code {proc.returncode}.")

        except FileNotFoundError:
            st.error("Could not find main.py. Run visualizer.py from the project directory.")
        except PermissionError:
            st.error("sudo permission denied. Add your user to sudoers.")

# ── LOAD DATA ──────────────────────────────────────────────────────────────────
data = None
if os.path.exists("results.json"):
    try:
        with open("results.json", "r") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        st.warning("results.json is malformed — re-run the traceroute.")

# ── MAIN LAYOUT ────────────────────────────────────────────────────────────────
col_map, col_out = st.columns([2, 1])

with col_map:
    st.subheader("Interactive Topology Map")

    # Protocol color legend
    st.markdown(
        "<small>"
        "<span style='color:#3b82f6'>&#9679; UDP</span> &nbsp;"
        "<span style='color:#ef4444'>&#9679; TCP</span> &nbsp;"
        "<span style='color:#22c55e'>&#9679; ICMP</span>"
        "</small>",
        unsafe_allow_html=True
    )

    m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB dark_matter")

    if data:
        proto_colors = {"UDP": "blue", "TCP": "red", "ICMP": "green"}

        for target, hops in data.items():
            path_coords = []
            for hop_series in hops:
                for probe in hop_series:
                    geo = probe.get("geo", {})
                    if geo.get("lat") and geo.get("lon"):
                        coord = [geo["lat"], geo["lon"]]
                        if coord not in path_coords:
                            path_coords.append(coord)
                            color = proto_colors.get(probe["protocol"], "white")
                            folium.CircleMarker(
                                location=coord,
                                radius=5,
                                color=color,
                                fill=True,
                                fill_opacity=0.8,
                                popup=folium.Popup(
                                    f"<b>{probe['ip']}</b><br>"
                                    f"Name: {probe['name']}<br>"
                                    f"RTT: {probe['rtt']} ms<br>"
                                    f"Protocol: {probe['protocol']}<br>"
                                    f"City: {geo.get('city', '?')}, {geo.get('country', '')}",
                                    max_width=220
                                )
                            ).add_to(m)

            if len(path_coords) > 1:
                folium.PolyLine(
                    path_coords, color="white", weight=1.5, opacity=0.5,
                    tooltip=f"Path to {target}"
                ).add_to(m)

    st_folium(m, width=None, height=550, use_container_width=True)

with col_out:
    # ── TAB 1: Raw output  TAB 2: Statistics ──────────────────────────────
    tab_raw, tab_stats = st.tabs(["Raw Output", "Hop Statistics"])

    with tab_raw:
        if data:
            lines = []
            for target, hops in data.items():
                lines.append(f"Tracing {target}...")
                for i, hop_series in enumerate(hops):
                    res    = hop_series[0]
                    status = f"{res['ip']} ({res['name']})" if res['ip'] else "*"
                    lines.append(f"  {i+1:2}  {status}  {res['rtt']} ms")
                lines.append("")
            st.code("\n".join(lines), language="text")
        else:
            st.info("No results yet. Configure options and click Start Traceroute.")

    with tab_stats:
        if data:
            for target, hops in data.items():
                st.markdown(f"**{target}**")
                rows = []
                for i, hop_series in enumerate(hops):
                    rtts   = [p["rtt"] for p in hop_series if p["rtt"] > 0]
                    rep_ip = next((p["ip"] for p in hop_series if p["ip"]), "*")
                    loss   = sum(1 for p in hop_series if not p["ip"])
                    rows.append({
                        "Hop":    i + 1,
                        "IP":     rep_ip,
                        "Min ms": round(min(rtts),                   2) if rtts else "—",
                        "Avg ms": round(sum(rtts) / len(rtts),       2) if rtts else "—",
                        "Max ms": round(max(rtts),                   2) if rtts else "—",
                        "Loss %": round(100 * loss / len(hop_series), 1),
                    })
                st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
<<<<<<< HEAD
            st.info("No results yet.")
=======
            st.info("No results yet.")
>>>>>>> bb4e9cd (updated visualizer)
