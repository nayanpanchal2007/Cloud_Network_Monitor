import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from network_monitor import (
    check_port,
    get_local_network_interfaces,
    get_network_traffic,
    monitor_host,
    validate_host,
)

st.set_page_config(
    page_title="Cloud Network Performance Monitor",
    page_icon="🌐",
    layout="wide",
)

st.markdown(
    """
    <style>
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .title {
            font-size: 2.6rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }
        .subtitle {
            font-size: 1.05rem;
            color: #8b8b8b;
            margin-bottom: 1.5rem;
        }
        .card {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 1rem;
            margin-top: 0.5rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if "history" not in st.session_state:
    st.session_state.history = []
if "results" not in st.session_state:
    st.session_state.results = []
if "monitoring_active" not in st.session_state:
    st.session_state.monitoring_active = False
if "last_monitor_tick" not in st.session_state:
    st.session_state.last_monitor_tick = time.monotonic()


def parse_hosts(raw_hosts: str) -> list[str]:
    return [line.strip() for line in raw_hosts.splitlines() if line.strip()]


def classify_latency(value, warning, critical):
    if value is None:
        return "Offline"
    if value >= critical:
        return "Critical"
    if value >= warning:
        return "Warning"
    return "Healthy"


def classify_loss(value, warning, critical):
    if value is None:
        return "Offline"
    if value >= critical:
        return "Critical"
    if value >= warning:
        return "Warning"
    return "Healthy"


def compute_health_score(results, latency_warning, latency_critical, packet_loss_warning, packet_loss_critical, jitter_warning):
    if not results:
        return 100

    score_total = 0.0
    for result in results:
        if result.get("status") == "Offline":
            score_total += 0
            continue

        average = result.get("average") or 0
        loss = result.get("packet_loss") or 0
        jitter = result.get("jitter") or 0
        availability = result.get("availability") or 0

        latency_score = 100
        if average > latency_warning:
            latency_score = max(0, 100 - ((average - latency_warning) / max(1, latency_critical - latency_warning)) * 100)

        loss_score = 100
        if loss > packet_loss_warning:
            loss_score = max(0, 100 - ((loss - packet_loss_warning) / max(1, packet_loss_critical - packet_loss_warning)) * 100)

        jitter_score = 100
        if jitter > jitter_warning:
            jitter_score = max(0, 100 - ((jitter - jitter_warning) / max(1, jitter_warning * 2)) * 100)

        availability_score = availability
        score_total += min(100, (latency_score * 0.35) + (loss_score * 0.30) + (jitter_score * 0.15) + (availability_score * 0.20))

    return int(round(score_total / len(results)))


def add_history_entry(result):
    st.session_state.history.append(
        {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Host": result.get("host", "N/A"),
            "Status": result.get("status", "Unknown"),
            "Average Latency (ms)": result.get("average"),
            "Minimum Latency (ms)": result.get("minimum"),
            "Maximum Latency (ms)": result.get("maximum"),
            "Packet Loss (%)": result.get("packet_loss"),
            "Jitter (ms)": result.get("jitter"),
            "Availability (%)": result.get("availability"),
        }
    )


def run_network_analysis(hosts, ping_count, timeout_ms):
    results = []
    for host in hosts:
        try:
            validate_host(host)
        except ValueError as exc:
            results.append(
                {
                    "host": host,
                    "status": "Invalid",
                    "sent": 0,
                    "received": 0,
                    "packet_loss": 100.0,
                    "average": None,
                    "minimum": None,
                    "maximum": None,
                    "jitter": None,
                    "availability": 0.0,
                    "latencies": [],
                    "message": str(exc),
                }
            )
            continue

        result = monitor_host(host, count=ping_count, timeout=timeout_ms)
        results.append(result)

    st.session_state.results = results
    for result in results:
        add_history_entry(result)

    return results


st.sidebar.title("🌐 Cloud Network Monitor")
st.sidebar.caption("Monitoring Configuration")

with st.sidebar:
    st.subheader("Target Hosts")
    default_hosts = "8.8.8.8\n1.1.1.1\ngoogle.com"
    host_input = st.text_area("Enter one host/IP per line", value=default_hosts, height=120)
    hosts = parse_hosts(host_input)

    st.subheader("Ping Configuration")
    ping_count = st.number_input("Packet count", min_value=1, max_value=20, value=5, step=1)
    timeout_ms = st.number_input("Timeout (ms)", min_value=500, max_value=5000, value=1000, step=100)

    st.subheader("Monitoring Mode")
    mode = st.radio("Select mode", ["Manual Analysis", "Continuous Monitoring"], horizontal=True)
    monitoring_interval = st.slider("Refresh interval (seconds)", min_value=5, max_value=60, value=10, step=5)

    st.subheader("TCP Monitoring")
    tcp_host = st.text_input("Host", value="google.com")
    tcp_port = st.number_input("Port", min_value=1, max_value=65535, value=443, step=1)

    st.subheader("Alert Thresholds")
    latency_warning = st.number_input("Latency warning threshold (ms)", min_value=10, max_value=5000, value=100, step=10)
    latency_critical = st.number_input("Latency critical threshold (ms)", min_value=20, max_value=10000, value=200, step=10)
    packet_loss_warning = st.number_input("Packet loss warning (%)", min_value=1, max_value=50, value=5, step=1)
    packet_loss_critical = st.number_input("Packet loss critical (%)", min_value=2, max_value=100, value=20, step=1)
    jitter_warning = st.number_input("Jitter warning (ms)", min_value=5, max_value=500, value=50, step=5)

    st.divider()
    run_button = st.button("Run Analysis", use_container_width=True)
    continuous_start = st.button("Start Monitoring", use_container_width=True)
    continuous_stop = st.button("Stop Monitoring", use_container_width=True)
    clear_history = st.button("Clear History", use_container_width=True)

    if clear_history:
        st.session_state.history = []
        st.session_state.results = []
        st.rerun()

    if continuous_stop:
        st.session_state.monitoring_active = False
        st.rerun()

    if continuous_start:
        st.session_state.monitoring_active = True
        st.session_state.last_monitor_tick = time.monotonic()
        st.rerun()

    if run_button:
        if not hosts:
            st.sidebar.warning("Add at least one target host to check.")
        else:
            try:
                run_network_analysis(hosts, ping_count, timeout_ms)
            except ValueError as exc:
                st.sidebar.error(str(exc))

    if tcp_host and tcp_port:
        if st.button("Test TCP Port", use_container_width=True):
            try:
                result = check_port(tcp_host, tcp_port, timeout=2)
                if result["status"] == "Open":
                    st.sidebar.success(f"{tcp_host}:{tcp_port} is open in {result['response']:.2f} ms.")
                elif result["status"] == "Closed":
                    st.sidebar.warning(f"{tcp_host}:{tcp_port} is closed. This does not necessarily mean the entire service is unavailable.")
                elif result["status"] == "Timeout":
                    st.sidebar.warning(f"Connection to {tcp_host}:{tcp_port} timed out.")
                else:
                    st.sidebar.error(f"Unable to test {tcp_host}:{tcp_port}. {result.get('message', '')}")
            except ValueError as exc:
                st.sidebar.error(str(exc))

if st.session_state.monitoring_active and mode == "Continuous Monitoring":
    next_attempt_due = st.session_state.last_monitor_tick + monitoring_interval
    if time.monotonic() >= next_attempt_due:
        if hosts:
            try:
                run_network_analysis(hosts, ping_count, timeout_ms)
            except ValueError as exc:
                st.warning(str(exc))
        st.session_state.last_monitor_tick = time.monotonic()
        st.rerun()

st.markdown('<div class="title">🌐 Cloud Network Performance Monitor</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Real-time network connectivity, performance, availability, and TCP port monitoring</div>', unsafe_allow_html=True)

results = st.session_state.results

if results:
    online_hosts = sum(1 for result in results if result.get("status") == "Online")
    total_hosts = len(results)
    avg_latencies = [result.get("average") for result in results if result.get("average") is not None]
    packet_losses = [result.get("packet_loss") for result in results]
    jitter_vals = [result.get("jitter") for result in results if result.get("jitter") is not None]

    overall_latency = sum(avg_latencies) / len(avg_latencies) if avg_latencies else 0
    overall_loss = sum(packet_losses) / len(packet_losses) if packet_losses else 0
    overall_jitter = sum(jitter_vals) / len(jitter_vals) if jitter_vals else 0
    availability = (online_hosts / total_hosts * 100) if total_hosts else 0
    health_score = compute_health_score(results, latency_warning, latency_critical, packet_loss_warning, packet_loss_critical, jitter_warning)

    metric_cols = st.columns(5)
    with metric_cols[0]:
        st.metric("🟢 Online Hosts", f"{online_hosts}/{total_hosts}")
    with metric_cols[1]:
        st.metric("⚡ Average Latency", f"{overall_latency:.2f} ms")
    with metric_cols[2]:
        st.metric("📦 Packet Loss", f"{overall_loss:.1f}%")
    with metric_cols[3]:
        st.metric("📈 Jitter", f"{overall_jitter:.2f} ms")
    with metric_cols[4]:
        st.metric("📡 Availability", f"{availability:.1f}%")

    st.caption("Application Health Score considers latency, packet loss, jitter and availability.")
    st.metric("🏥 Application Health Score", f"{health_score} / 100")
    st.divider()

    host_table_rows = []
    for result in results:
        host = result.get("host", "N/A")
        avg = result.get("average")
        packet_loss = result.get("packet_loss")
        jitter = result.get("jitter")
        availability_value = result.get("availability")

        if result.get("status") == "Offline":
            alert_status = "🔴 Offline"
        elif packet_loss is not None and packet_loss >= packet_loss_critical:
            alert_status = "🔴 Critical"
        elif avg is not None and avg >= latency_critical:
            alert_status = "🔴 Critical"
        elif avg is not None and avg >= latency_warning:
            alert_status = "🟡 Warning"
        elif packet_loss is not None and packet_loss >= packet_loss_warning:
            alert_status = "🟡 Warning"
        elif jitter is not None and jitter >= jitter_warning:
            alert_status = "🟡 Warning"
        else:
            alert_status = "🟢 Healthy"

        host_table_rows.append(
            {
                "Host": host,
                "Status": alert_status,
                "Average Latency": f"{avg:.2f} ms" if avg is not None else "N/A",
                "Minimum": f"{result.get('minimum'):.2f} ms" if result.get("minimum") is not None else "N/A",
                "Maximum": f"{result.get('maximum'):.2f} ms" if result.get("maximum") is not None else "N/A",
                "Packet Loss": f"{packet_loss:.1f}%" if packet_loss is not None else "N/A",
                "Jitter": f"{jitter:.2f} ms" if jitter is not None else "N/A",
                "Availability": f"{availability_value:.1f}%" if availability_value is not None else "N/A",
            }
        )

    st.subheader("📡 Host Monitoring Results")
    st.dataframe(pd.DataFrame(host_table_rows), use_container_width=True, hide_index=True)

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        latency_chart = pd.DataFrame({
            "Host": [item["host"] for item in results],
            "Average Latency (ms)": [item["average"] if item["average"] is not None else 0 for item in results],
        })
        st.subheader("Average Latency by Host")
        fig_latency = px.bar(latency_chart, x="Host", y="Average Latency (ms)", text_auto=".2f", color="Host")
        fig_latency.update_layout(xaxis_title="Host", yaxis_title="Latency (ms)")
        st.plotly_chart(fig_latency, use_container_width=True)

    with chart_col2:
        loss_chart = pd.DataFrame({
            "Host": [item["host"] for item in results],
            "Packet Loss (%)": [item["packet_loss"] if item["packet_loss"] is not None else 0 for item in results],
        })
        st.subheader("Packet Loss Percentage")
        fig_loss = px.bar(loss_chart, x="Host", y="Packet Loss (%)", text_auto=".1f", color="Host")
        fig_loss.update_layout(xaxis_title="Host", yaxis_title="Packet Loss (%)")
        st.plotly_chart(fig_loss, use_container_width=True)

    chart_col3, chart_col4 = st.columns(2)
    with chart_col3:
        jitter_chart = pd.DataFrame({
            "Host": [item["host"] for item in results],
            "Jitter (ms)": [item["jitter"] if item["jitter"] is not None else 0 for item in results],
        })
        st.subheader("Jitter Comparison")
        fig_jitter = px.bar(jitter_chart, x="Host", y="Jitter (ms)", text_auto=".2f", color="Host")
        fig_jitter.update_layout(xaxis_title="Host", yaxis_title="Jitter (ms)")
        st.plotly_chart(fig_jitter, use_container_width=True)

    with chart_col4:
        availability_chart = pd.DataFrame({
            "Host": [item["host"] for item in results],
            "Availability (%)": [item["availability"] if item["availability"] is not None else 0 for item in results],
        })
        st.subheader("Availability Comparison")
        fig_availability = px.bar(availability_chart, x="Host", y="Availability (%)", text_auto=".1f", color="Host")
        fig_availability.update_layout(xaxis_title="Host", yaxis_title="Availability (%)")
        st.plotly_chart(fig_availability, use_container_width=True)

    latency_hist = pd.DataFrame({
        "Host": [item["host"] for item in results],
        "Minimum Latency (ms)": [item["minimum"] if item["minimum"] is not None else 0 for item in results],
        "Maximum Latency (ms)": [item["maximum"] if item["maximum"] is not None else 0 for item in results],
    })
    st.subheader("Minimum vs Maximum Latency")
    fig_minmax = px.line(latency_hist, x="Host", y=["Minimum Latency (ms)", "Maximum Latency (ms)"], markers=True)
    fig_minmax.update_layout(xaxis_title="Host", yaxis_title="Latency (ms)")
    st.plotly_chart(fig_minmax, use_container_width=True)

    st.subheader("💻 Local Network Interface")
    interface_rows = get_local_network_interfaces()
    if interface_rows:
        st.dataframe(pd.DataFrame(interface_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No network interface information could be retrieved from this system.")

    st.subheader("📦 Network Traffic Statistics")
    traffic = get_network_traffic()
    traffic_cols = st.columns(4)
    for idx, key in enumerate(["Bytes Sent", "Bytes Received", "Packets Sent", "Packets Received"]):
        with traffic_cols[idx]:
            value = traffic.get(key, "N/A")
            if isinstance(value, (int, float)):
                st.metric(key, f"{value:,}")
            else:
                st.metric(key, value)

    st.divider()
    st.subheader("🔌 TCP Port Monitoring")
    if st.button("Test Selected Port", use_container_width=True):
        port_result = check_port(tcp_host, tcp_port, timeout=2)
        if port_result["status"] == "Open":
            st.success(f"{tcp_host}:{tcp_port} is OPEN. Response: {port_result['response']:.2f} ms")
        elif port_result["status"] == "Closed":
            st.warning(f"{tcp_host}:{tcp_port} is CLOSED. This only tells us that the port is not accepting connections; it does not mean the host is completely unavailable.")
        elif port_result["status"] == "Timeout":
            st.warning(f"The TCP check for {tcp_host}:{tcp_port} timed out.")
        else:
            st.error(f"The TCP check could not be completed. {port_result.get('message', '')}")

    st.divider()
    if st.session_state.history:
        st.subheader("📈 Monitoring History")
        history_df = pd.DataFrame(st.session_state.history)
        st.dataframe(history_df, use_container_width=True, hide_index=True)
        csv_data = history_df.to_csv(index=False)
        st.download_button("Export CSV", csv_data, file_name="network_monitor_history.csv", mime="text/csv")

else:
    st.info("Configure hosts in the sidebar and click Run Analysis to begin monitoring.")

st.caption("Cloud Network Monitoring System | Computer Networks Experiment 10 | Version 3")

