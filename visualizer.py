import streamlit as st
import json
import folium
from streamlit_folium import st_folium
import os

# Page Config
st.set_page_config(layout="wide", page_title="Internet Topology Explorer")

st.title("🌐 Internet Topology Explorer")

# --- LEFT SIDEBAR: INPUT ---
with st.sidebar:
    st.header("1. Input Configuration")
    target_file = st.file_uploader("Upload targets.txt", type=["txt"])
    max_ttl = st.slider("Max TTL", 1, 60, 30)
    num_series = st.number_input("Series per Hop", 1, 5, 1)
    
    if st.button("🚀 Start Traceroute"):
        st.info("In a real app, this would trigger main.py via subprocess.")
        # For now, we will load the existing results.json
        if os.path.exists("results.json"):
            st.success("Loaded data from results.json")
        else:
            st.error("results.json not found. Run main.py first!")

# --- LAYOUT: MAP (Center) and OUTPUT (Right) ---
col_map, col_out = st.columns([2, 1])

with col_map:
    st.subheader("Interactive Topology Map")
    
    # Initialize Map
    m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB dark_matter")
    
    if os.path.exists("results.json"):
        with open("results.json", "r") as f:
            data = json.load(f)
        
        # Draw paths on map
        for target, hops in data.items():
            path_coords = []
            for hop_series in hops:
                for probe in hop_series:
                    geo = probe.get("geo", {})
                    if geo.get("lat") and geo.get("lon"):
                        coord = [geo["lat"], geo["lon"]]
                        if coord not in path_coords:
                            path_coords.append(coord)
                            # Protocol-based coloring
                            color = "blue" if probe["protocol"] == "UDP" else "red" if probe["protocol"] == "TCP" else "green"
                            folium.CircleMarker(
                                location=coord,
                                radius=5,
                                color=color,
                                popup=f"IP: {probe['ip']}<br>RTT: {probe['rtt']}ms"
                            ).add_to(m)
            
            if len(path_coords) > 1:
                folium.PolyLine(path_coords, color="white", weight=1, opacity=0.5).add_to(m)

    st_folium(m, width=800, height=600)

with col_out:
    st.subheader("Raw Terminal Output")
    if os.path.exists("results.json"):
        # Format the JSON data to look like Figure 1
        output_text = ""
        for target, hops in data.items():
            output_text += f"Tracing {target}...\n"
            for i, hop_series in enumerate(hops):
                res = hop_series[0] # Show first probe info
                status = f"{res['ip']} ({res['name']})" if res['ip'] else "*"
                output_text += f"{i+1}  {status}  {res['rtt']} ms\n"
        
        st.code(output_text, language="text")
    else:
        st.write("No results to display yet.")