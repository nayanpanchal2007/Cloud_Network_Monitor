# Cloud-Based Network Performance Monitoring System

## Problem Statement
Modern network performance depends on smooth connectivity, low latency, and predictable packet delivery. In cloud and distributed systems, administrators need a quick way to monitor remote hosts, detect packet loss, and validate service reachability. This project provides a local dashboard for monitoring IP addresses and hostnames in a way suitable for a Computer Networks mini-project.

## Objectives
- Monitor multiple hosts for reachability and performance
- Measure latency, packet loss, jitter, and availability
- Inspect TCP port reachability on selected services
- Display local interface and traffic statistics
- Present results in a professional dashboard
- Support both manual and continuous monitoring

## Features
- ICMP host monitoring using the system ping command
- Multiple target support in one dashboard
- TCP port testing for common and custom ports
- Monitoring history with export to CSV
- Alert thresholds for latency, packet loss, and jitter
- Application health score based on measured values
- Local network interface and traffic overview
- Streamlit-based cloud-ready dashboard

## Technologies Used
- Python 3
- Streamlit
- Pandas
- Plotly
- psutil
- Socket programming
- Operating system ICMP ping utility

## System Architecture
The application uses a lightweight client-side dashboard that reads target host values, runs ICMP and TCP checks, and presents summarized results in a web interface. The logic is split between:

- app.py: dashboard layout, controls, charts, and history
- network_monitor.py: validation, ping logic, TCP checks, and interface statistics

## Network Architecture
The project demonstrates multiple networking concepts:
- IP addressing and hostname resolution via DNS
- ICMP connectivity checks
- TCP connections to open or closed ports
- Client-server communication patterns
- Latency, packet loss, and jitter estimation
- Monitoring of local network interfaces and traffic counters

## How the Application Works
1. The user enters target hosts in the sidebar.
2. The dashboard validates each host input.
3. ICMP ping requests are sent to each host.
4. Statistics such as latency, packet loss, jitter, and availability are calculated.
5. TCP port checks are performed separately for service reachability.
6. Result summaries are displayed in KPI cards, tables, and charts.
7. Monitoring history can be exported as CSV.

## Protocols Used
- ICMP: connectivity and latency testing
- TCP: port connectivity testing
- DNS: hostname resolution
- HTTP/HTTPS: access to the Streamlit dashboard itself

## Installation Instructions
1. Clone or download the project.
2. Open a terminal in the project folder.
3. Create a virtual environment if needed.
4. Install dependencies:

   pip install -r requirements.txt

## How to Run
From the project root:

   streamlit run app.py

Then open the local Streamlit URL shown in the terminal.

## Example Usage
- Test public DNS servers such as 8.8.8.8 and 1.1.1.1
- Check a web service such as google.com
- Validate a TCP port like 443 or 80
- Run continuous monitoring with a selected refresh interval

## Testing
The project should be tested using real network conditions. A basic smoke test may include:
- Public hosts like 8.8.8.8 and 1.1.1.1
- Hostnames such as google.com
- Invalid hostnames or malformed addresses
- Closed TCP ports such as 21 or 3307
- A valid port like 443 on google.com
- Continuous monitoring start/stop behavior

## Limitations
- ICMP may be blocked by some networks or firewalls.
- Port results depend on host and network policies.
- Some network conditions can make measurements fluctuate.
- The dashboard is for educational and monitoring use, not for production-grade SLA tracking.

## Future Scope
- Alerts via email or notifications
- Historical trend charts with long-term storage
- Multi-user or remote deployment on cloud platforms
- Integration with SNMP or REST APIs for enterprise monitoring
- Better anomaly detection using statistical baselines

## Running in VS Code
Open the project in VS Code, install the Python extension, select the project interpreter, then run:

   streamlit run app.py

## Notes
This application intentionally avoids collecting credentials or secrets. It supports real measurement collection without hard-coded account details or external API keys.
