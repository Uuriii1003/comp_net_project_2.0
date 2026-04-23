# Installation & Operational Guide: Internet Topology Explorer

This guide covers the prerequisites, installation steps, and operational instructions for the **Internet Topology Explorer**.

---

## 1. Prerequisites
Before you begin, ensure your system meets the following requirements:

* **Python 3.12** (or higher)
* **Sudo/Root Privileges**: Required for **Scapy** to perform raw packet injection and network sniffing.

---

## 2. Installation Steps
Follow these steps to set up your environment:

### Step 1: Install Dependencies
Run the following command to install the required libraries:
```bash
pip install streamlit scapy pandas streamlit-folium folium streamlit-agraph
```
> **Note:** If a `Makefile` is provided in your directory, you can simply run `make install`.

### Step 2: Run the Analyzer
To launch the dashboard, you must run Streamlit with root privileges:
```bash
sudo streamlit run visualizer.py
```

---

## 3. Using the Explorer
Once the application opens in your browser, follow these steps to begin your analysis:

### I. Input Target
* **Single IP:** Enter a target address (e.g., `8.8.8.8`).
* **Batch Upload:** Upload a `.txt` file containing multiple targets.

### II. Adjust the 6 Core Arguments
| Argument | Description |
| :--- | :--- |
| **Min/Max TTL** | Defines the hop range for the traceroute. |
| **Series/Hop** | Number of probes sent to each hop. |
| **Packet Size** | The size of the probe in bytes. |
| **Timeout** | Seconds to wait for a response before skipping. |
| **Wait Time** | Delay between individual probes to avoid rate-limiting. |

### III. Launch
Click the **"Launch Traceroute"** button to begin the scan.

---

## 4. Navigation & Analysis
The Explorer provides three primary views for interpreting network data:

* **Geographic Map:** Displays the physical path of packets. Hover over markers to view **6-point metrics**: *Hop #, IP, Hostname, Protocol, RTT, and Loss Rate.*
* **Logical Topology:** A node-link graph of the network. **Link thickness** scales with speed; thicker lines indicate lower RTT (faster connections).
* **Data & Logs:** Use the built-in search bar to filter specific nodes or download the raw trace report for offline analysis.

---

## 5. Maintenance
To clear temporary JSON data, target lists, and Python cache files, run:
```bash
make clean
```

> [!IMPORTANT]  
> **Permission Denied?** If you encounter this error, ensure you are using `sudo`. Raw socket manipulation is restricted to root users on most Unix-like systems.
