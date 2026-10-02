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
            font-size: 2.8rem;
            font-weight: 800;
            letter-spacing: 0.05em;
            line-height: 1.08;
            margin-bottom: 0.2rem;
        }
        .subtitle {
            font-size: 1.05rem;
            color: #b8c1d9;
            margin-bottom: 1.5rem;
        }
        .kpi-card {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.75), rgba(15, 23, 42, 0.95));
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 14px;
            padding: 1rem 1rem 0.85rem;
            height: 100%;
            box-shadow: 0 10px 25px rgba(15, 23, 42, 0.25);
        }
        .kpi-label {
            font-size: 0.72rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #a5b4cf;
            margin-bottom: 0.4rem;
        }
        .kpi-value {
            font-size: 1.7rem;
            font-weight: 700;
            color: #f8fafc;
            line-height: 1.2;
        }
        .health-card {
            background: rgba(15, 23, 42, 0.72);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 14px;
            padding: 1rem;
            margin-top: 0.6rem;
        }
        .status-pill {
            display: inline-block;
            padding: 0.28rem 0.7rem;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.82rem;
        }
        .overview-box {
            background: rgba(15, 23, 42, 0.72);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 12px;
            padding: 0.9rem 1rem;
            height: 100%;
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


def determine_host_status(result, latency_warning, latency_critical, packet_loss_warning, packet_loss_critical, jitter_warning):
    if result.get("status") == "Offline":
        return "⚫ Offline"
    average = result.get("average")
    packet_loss = result.get("packet_loss")
    jitter = result.get("jitter")

    if packet_loss is not None and packet_loss >= packet_loss_critical:
        return "🔴 Critical"
    if average is not None and average >= latency_critical:
        return "🔴 Critical"
    if average is not None and average >= latency_warning:
        return "🟡 Warning"
    if packet_loss is not None and packet_loss >= packet_loss_warning:
        return "🟡 Warning"
    if jitter is not None and jitter >= jitter_warning:
        return "🟡 Warning"
    return "🟢 Healthy"


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


if "tcp_test_result" not in st.session_state:
    st.session_state.tcp_test_result = None

st.sidebar.title("🌐 CLOUD NETWORK")
st.sidebar.caption("Performance Monitor")

with st.sidebar:
    with st.expander("🌐 Monitoring Targets", expanded=True):
        default_hosts = "8.8.8.8\n1.1.1.1\ngoogle.com"
        host_input = st.text_area("Hosts", value=default_hosts, height=120)
        hosts = parse_hosts(host_input)
        ping_count = st.number_input("Ping count", min_value=1, max_value=20, value=5, step=1)
        timeout_ms = st.number_input("Timeout", min_value=500, max_value=5000, value=1000, step=100)

    with st.expander("⚙️ Monitoring Settings", expanded=True):
        mode = st.radio("Mode", ["Manual / Continuous", "Continuous Monitoring"], horizontal=True)
        monitoring_interval = st.slider("Refresh interval (seconds)", min_value=5, max_value=60, value=10, step=5)

    with st.expander("🔌 TCP Port Test", expanded=True):
        tcp_host = st.text_input("Host", value="google.com")
        tcp_port = st.number_input("Port", min_value=1, max_value=65535, value=443, step=1)

    with st.expander("🚨 Alert Thresholds", expanded=True):
        latency_warning = st.number_input("Latency warning (ms)", min_value=10, max_value=5000, value=100, step=10)
        latency_critical = st.number_input("Latency critical (ms)", min_value=20, max_value=10000, value=200, step=10)
        packet_loss_warning = st.number_input("Packet loss warning (%)", min_value=1, max_value=50, value=5, step=1)
        packet_loss_critical = st.number_input("Packet loss critical (%)", min_value=2, max_value=100, value=20, step=1)
        jitter_warning = st.number_input("Jitter warning (ms)", min_value=5, max_value=500, value=50, step=5)

    with st.expander("🛠 Actions", expanded=True):
        run_button = st.button("Run Analysis", use_container_width=True)
        continuous_start = st.button("Start Monitoring", use_container_width=True)
        continuous_stop = st.button("Stop Monitoring", use_container_width=True)
        clear_history = st.button("Clear History", use_container_width=True)
        if st.button("Test TCP Port", use_container_width=True):
            try:
                st.session_state.tcp_test_result = check_port(tcp_host, tcp_port, timeout=2)
            except ValueError as exc:
                st.session_state.tcp_test_result = {"status": "Error", "message": str(exc)}

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

st.markdown('<div class="title">CLOUD NETWORK<br>PERFORMANCE MONITOR</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Real-time connectivity, latency, reliability and TCP service monitoring</div>', unsafe_allow_html=True)

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

    if health_score >= 80:
        health_status = "🟢 Healthy"
    elif health_score >= 50:
        health_status = "🟡 Warning"
    else:
        health_status = "🔴 Critical"

    metric_cols = st.columns(5)
    with metric_cols[0]:
        st.markdown('<div class="kpi-card"><div class="kpi-label">ONLINE HOSTS</div><div class="kpi-value">{}</div></div>'.format(f"{online_hosts}/{total_hosts}"), unsafe_allow_html=True)
    with metric_cols[1]:
        st.markdown('<div class="kpi-card"><div class="kpi-label">AVERAGE LATENCY</div><div class="kpi-value">{:.2f} ms</div></div>'.format(overall_latency), unsafe_allow_html=True)
    with metric_cols[2]:
        st.markdown('<div class="kpi-card"><div class="kpi-label">PACKET LOSS</div><div class="kpi-value">{:.1f}%</div></div>'.format(overall_loss), unsafe_allow_html=True)
    with metric_cols[3]:
        st.markdown('<div class="kpi-card"><div class="kpi-label">JITTER</div><div class="kpi-value">{:.2f} ms</div></div>'.format(overall_jitter), unsafe_allow_html=True)
    with metric_cols[4]:
        st.markdown('<div class="kpi-card"><div class="kpi-label">AVAILABILITY</div><div class="kpi-value">{:.1f}%</div></div>'.format(availability), unsafe_allow_html=True)

    st.markdown("<hr style='margin: 1.5rem 0 1.2rem 0;' />", unsafe_allow_html=True)
    health_cols = st.columns([2, 3])
    with health_cols[0]:
        st.markdown(
            '<div class="health-card"><div class="kpi-label">Application Health Score</div><div class="kpi-value">{} / 100</div><div style="margin-top:0.7rem"><span class="status-pill">{}</span></div></div>'.format(health_score, health_status),
            unsafe_allow_html=True,
        )
    with health_cols[1]:
        st.markdown(
            '<div class="health-card"><div class="kpi-label">Status</div><div style="font-size:1rem; color:#dbe4f8; margin-top:0.2rem;">Based on latency, packet loss, jitter and availability.</div></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    healthy_hosts = sum(1 for result in results if determine_host_status(result, latency_warning, latency_critical, packet_loss_warning, packet_loss_critical, jitter_warning).startswith("🟢"))
    warning_hosts = sum(1 for result in results if determine_host_status(result, latency_warning, latency_critical, packet_loss_warning, packet_loss_critical, jitter_warning).startswith("🟡"))
    critical_hosts = sum(1 for result in results if determine_host_status(result, latency_warning, latency_critical, packet_loss_warning, packet_loss_critical, jitter_warning).startswith("🔴"))
    offline_hosts = sum(1 for result in results if determine_host_status(result, latency_warning, latency_critical, packet_loss_warning, packet_loss_critical, jitter_warning).startswith("⚫"))

    st.subheader("📊 Network Health Overview")
    overview_cols = st.columns(4)
    overview_values = [("Healthy Hosts", healthy_hosts), ("Warning Hosts", warning_hosts), ("Critical Hosts", critical_hosts), ("Offline Hosts", offline_hosts)]
    for idx, (label, value) in enumerate(overview_values):
        with overview_cols[idx]:
            st.markdown(f'<div class="overview-box"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div>', unsafe_allow_html=True)

    st.divider()

    host_table_rows = []
    for result in results:
        host = result.get("host", "N/A")
        avg = result.get("average")
        packet_loss = result.get("packet_loss")
        jitter = result.get("jitter")
        availability_value = result.get("availability")
        alert_status = determine_host_status(result, latency_warning, latency_critical, packet_loss_warning, packet_loss_critical, jitter_warning)

        host_table_rows.append(
            {
                "Host": host,
                "Status": alert_status,
                "Average": f"{avg:.2f} ms" if avg is not None else "N/A",
                "Min": f"{result.get('minimum'):.2f} ms" if result.get("minimum") is not None else "N/A",
                "Max": f"{result.get('maximum'):.2f} ms" if result.get("maximum") is not None else "N/A",
                "Packet Loss": f"{packet_loss:.1f}%" if packet_loss is not None else "N/A",
                "Jitter": f"{jitter:.2f} ms" if jitter is not None else "N/A",
                "Availability": f"{availability_value:.1f}%" if availability_value is not None else "N/A",
            }
        )

    st.subheader("📡 Host Monitoring Results")
    st.dataframe(pd.DataFrame(host_table_rows, columns=["Host", "Status", "Average", "Min", "Max", "Packet Loss", "Jitter", "Availability"]), use_container_width=True, hide_index=True)

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        latency_chart = pd.DataFrame({
            "Host": [item["host"] for item in results],
            "Latency (ms)": [item["average"] if item["average"] is not None else 0 for item in results],
        })
        st.subheader("Average Latency by Host")
        fig_latency = px.bar(
            latency_chart,
            x="Host",
            y="Latency (ms)",
            color="Host",
            text=[f"{value:.2f}" if value is not None else "N/A" for value in latency_chart["Latency (ms)"]],
            hover_name="Host",
        )
        fig_latency.update_traces(texttemplate="%{text} ms", textposition="outside")
        fig_latency.update_layout(
            xaxis_title="Host",
            yaxis_title="Latency (ms)",
            template="plotly_dark",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig_latency, use_container_width=True)

    with chart_col2:
        loss_chart = pd.DataFrame({
            "Host": [item["host"] for item in results],
            "Packet Loss (%)": [item["packet_loss"] if item["packet_loss"] is not None else 0 for item in results],
        })
        st.subheader("Packet Loss")
        fig_loss = px.bar(
            loss_chart,
            x="Host",
            y="Packet Loss (%)",
            color="Host",
            text=[f"{value:.1f}%" for value in loss_chart["Packet Loss (%)"]],
            hover_name="Host",
        )
        fig_loss.update_traces(texttemplate="%{text}", textposition="outside")
        loss_max = max(loss_chart["Packet Loss (%)"].max(), 10.0)
        fig_loss.update_layout(
            xaxis_title="Host",
            yaxis_title="Packet Loss (%)",
            template="plotly_dark",
            yaxis=dict(range=[-max(loss_max * 0.15, 1.0), loss_max * 1.2]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig_loss, use_container_width=True)

    chart_col3, chart_col4 = st.columns(2)
    with chart_col3:
        jitter_chart = pd.DataFrame({
            "Host": [item["host"] for item in results],
            "Jitter (ms)": [item["jitter"] if item["jitter"] is not None else 0 for item in results],
        })
        st.subheader("Jitter Comparison")
        fig_jitter = px.bar(
            jitter_chart,
            x="Host",
            y="Jitter (ms)",
            color="Host",
            text=[f"{value:.2f}" for value in jitter_chart["Jitter (ms)"]],
            hover_name="Host",
        )
        fig_jitter.update_traces(texttemplate="%{text} ms", textposition="outside")
        fig_jitter.update_layout(
            xaxis_title="Host",
            yaxis_title="Jitter (ms)",
            template="plotly_dark",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig_jitter, use_container_width=True)

    with chart_col4:
        availability_chart = pd.DataFrame({
            "Host": [item["host"] for item in results],
            "Availability (%)": [item["availability"] if item["availability"] is not None else 0 for item in results],
        })
        st.subheader("Availability Comparison")
        fig_availability = px.bar(
            availability_chart,
            x="Host",
            y="Availability (%)",
            color="Host",
            text=[f"{value:.1f}%" for value in availability_chart["Availability (%)"]],
            hover_name="Host",
        )
        fig_availability.update_traces(texttemplate="%{text}", textposition="outside")
        fig_availability.update_layout(
            xaxis_title="Host",
            yaxis_title="Availability (%)",
            template="plotly_dark",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig_availability, use_container_width=True)

    latency_hist = pd.DataFrame({
        "Host": [item["host"] for item in results],
        "Minimum Latency (ms)": [item["minimum"] if item["minimum"] is not None else 0 for item in results],
        "Maximum Latency (ms)": [item["maximum"] if item["maximum"] is not None else 0 for item in results],
    })
    st.subheader("Minimum vs Maximum Latency")
    fig_minmax = px.line(
        latency_hist,
        x="Host",
        y=["Minimum Latency (ms)", "Maximum Latency (ms)"],
        markers=True,
        hover_data={"Host": True, "Minimum Latency (ms)": ":.2f", "Maximum Latency (ms)": ":.2f"},
    )
    fig_minmax.update_traces(mode="lines+markers+text", textposition="top center")
    fig_minmax.update_layout(
        xaxis_title="Host",
        yaxis_title="Latency (ms)",
        template="plotly_dark",
        legend_title_text="Latency Type",
        margin=dict(l=20, r=20, t=30, b=20),
    )
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
    st.subheader("🔌 TCP SERVICE TEST")
    if st.session_state.tcp_test_result:
        tcp_result = st.session_state.tcp_test_result
        status = tcp_result.get("status", "Unknown")
        response = tcp_result.get("response")
        color = "green" if status == "Open" else "red" if status in {"Closed", "Timeout", "Error"} else "gray"
        if status == "Open":
            status_label = "🟢 OPEN"
            response_text = f"{response:.2f} ms" if response is not None else "N/A"
        elif status == "Closed":
            status_label = "🔴 CLOSED"
            response_text = "Connection refused"
        elif status == "Timeout":
            status_label = "🟠 TIMEOUT"
            response_text = f"{response:.2f} ms" if response is not None else "N/A"
        else:
            status_label = "⚫ ERROR"
            response_text = tcp_result.get("message", "Unable to determine result")
        st.markdown(
            f'<div class="health-card" style="border-color: {color};"><div class="kpi-label">TCP Service Test</div><div style="font-size:1.15rem; font-weight:700; margin-top:0.25rem;">Host: {tcp_host}</div><div style="font-size:1.05rem; margin-top:0.2rem;">Port: {tcp_port}</div><div style="font-size:1.1rem; margin-top:0.6rem;">Status: {status_label}</div><div style="font-size:1.05rem; margin-top:0.2rem;">Response Time: {response_text}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Run the TCP port test from the sidebar to display service results.")

    st.divider()
    if st.session_state.history:
        st.subheader("📈 Monitoring History")
        history_df = pd.DataFrame(st.session_state.history)
        st.dataframe(history_df, use_container_width=True, hide_index=True)
        csv_data = history_df.to_csv(index=False)
        st.download_button("Export CSV", csv_data, file_name="network_monitor_history.csv", mime="text/csv")

else:
    st.info("Configure hosts in the sidebar and click Run Analysis to begin monitoring.")

st.caption("Cloud Network Monitoring System | Version 4")

