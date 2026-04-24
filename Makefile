# Makefile for Computer Network Project

install:
	pip install streamlit scapy pandas streamlit-folium folium streamlit-agraph

run:
	sudo streamlit run visualizer.py

clean:
	rm -rf __pycache__ src/__pycache__
	rm -f data/results.json data/raw_output.txt data/topology.json targets_current.txt

.PHONY: install run clean