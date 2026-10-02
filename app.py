import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from network_monitor import monitor_host, check_port


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="Cloud Network Monitor",
    page_icon="🌐",
    layout="wide"
)


# ==================================================
# CUSTOM CSS
# ==================================================

st.markdown("""
<style>

.main-title {
    font-size: 42px;
    font-weight: 700;
}

.subtitle {
    font-size: 18px;
    color: #8b8b8b;
    margin-bottom: 25px;
}

.metric-card {
    padding: 15px;
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)


# ==================================================
# HEADER
# ==================================================

st.markdown(
    '<div class="main-title">'
    '🌐 Cloud Network Monitoring System'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Real-time network connectivity, latency, packet loss '
    'and TCP performance analysis'
    '</div>',
    unsafe_allow_html=True
)


# ==================================================
# SESSION STATE
# ==================================================

if "history" not in st.session_state:
    st.session_state.history = []

if "results" not in st.session_state:
    st.session_state.results = []


# ==================================================
# SIDEBAR
# ==================================================

st.sidebar.title("⚙️ Monitoring Settings")

st.sidebar.subheader("🌐 Hosts")

default_hosts = """8.8.8.8
1.1.1.1
google.com"""

host_input = st.sidebar.text_area(
    "Enter one host per line",
    value=default_hosts,
    height=120
)

hosts = [
    host.strip()
    for host in host_input.splitlines()
    if host.strip()
]

ping_count = st.sidebar.slider(
    "Ping Attempts",
    min_value=3,
    max_value=10,
    value=5
)

st.sidebar.divider()

st.sidebar.subheader("🔌 TCP Port Test")

port_host = st.sidebar.text_input(
    "TCP Host",
    value="google.com"
)

port = st.sidebar.selectbox(
    "Port",
    [53, 80, 443, 22, 25, 3306]
)

check_button = st.sidebar.button(
    "🔍 Run Network Analysis",
    use_container_width=True
)


# ==================================================
# RUN NETWORK ANALYSIS
# ==================================================

if check_button:

    results = []

    progress = st.progress(0)

    for index, host in enumerate(hosts):

        result = monitor_host(
            host,
            ping_count
        )

        results.append(result)

        progress.progress(
            (index + 1) / len(hosts)
        )

    progress.empty()

    st.session_state.results = results

    # Store history

    timestamp = datetime.now().strftime(
        "%H:%M:%S"
    )

    for result in results:

        st.session_state.history.append({

            "Time": timestamp,

            "Host": result["host"],

            "Status": result["status"],

            "Average": result["average"],

            "Minimum": result["minimum"],

            "Maximum": result["maximum"],

            "Packet Loss": result["packet_loss"],

            "Jitter": result["jitter"]

        })


# ==================================================
# CURRENT RESULTS
# ==================================================

results = st.session_state.results


if results:

    # ------------------------------------------------
    # Overall Statistics
    # ------------------------------------------------

    online_hosts = sum(
        1
        for result in results
        if result["status"] == "Online"
    )

    total_hosts = len(results)

    all_latencies = [
        result["average"]
        for result in results
        if result["average"] is not None
    ]

    all_losses = [
        result["packet_loss"]
        for result in results
    ]

    all_jitters = [
        result["jitter"]
        for result in results
        if result["jitter"] is not None
    ]

    overall_latency = (
        sum(all_latencies) / len(all_latencies)
        if all_latencies
        else 0
    )

    overall_loss = (
        sum(all_losses) / len(all_losses)
        if all_losses
        else 100
    )

    overall_jitter = (
        sum(all_jitters) / len(all_jitters)
        if all_jitters
        else 0
    )

    availability = (
        online_hosts / total_hosts * 100
        if total_hosts
        else 0
    )


    # ------------------------------------------------
    # KPI CARDS
    # ------------------------------------------------

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:

        st.metric(
            "🟢 Online Hosts",
            f"{online_hosts}/{total_hosts}"
        )

    with col2:

        st.metric(
            "⚡ Avg Latency",
            f"{overall_latency:.2f} ms"
        )

    with col3:

        st.metric(
            "📦 Packet Loss",
            f"{overall_loss:.1f}%"
        )

    with col4:

        st.metric(
            "📈 Jitter",
            f"{overall_jitter:.2f} ms"
        )

    with col5:

        st.metric(
            "📡 Availability",
            f"{availability:.1f}%"
        )


    st.divider()


    # ==================================================
    # HOST MONITORING TABLE
    # ==================================================

    st.subheader("📡 Host Monitoring")

    host_data = []

    for result in results:

        host_data.append({

            "Host":
                result["host"],

            "Status":
                "🟢 Online"
                if result["status"] == "Online"
                else "🔴 Offline",

            "Average":
                (
                    f'{result["average"]:.2f} ms'
                    if result["average"] is not None
                    else "N/A"
                ),

            "Minimum":
                (
                    f'{result["minimum"]:.2f} ms'
                    if result["minimum"] is not None
                    else "N/A"
                ),

            "Maximum":
                (
                    f'{result["maximum"]:.2f} ms'
                    if result["maximum"] is not None
                    else "N/A"
                ),

            "Packet Loss":
                f'{result["packet_loss"]:.1f}%',

            "Jitter":
                (
                    f'{result["jitter"]:.2f} ms'
                    if result["jitter"] is not None
                    else "N/A"
                )

        })

    host_df = pd.DataFrame(host_data)

    st.dataframe(
        host_df,
        use_container_width=True,
        hide_index=True
    )


    # ==================================================
    # LATENCY COMPARISON
    # ==================================================

    st.subheader("📊 Latency Comparison")

    chart_data = pd.DataFrame({

        "Host": [
            result["host"]
            for result in results
        ],

        "Average Latency": [
            result["average"] or 0
            for result in results
        ]

    })

    fig = px.bar(
        chart_data,
        x="Host",
        y="Average Latency",
        title="Average Network Latency",
        text_auto=".2f"
    )

    fig.update_layout(
        xaxis_title="Host",
        yaxis_title="Latency (ms)"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


    # ==================================================
    # PACKET LOSS
    # ==================================================

    st.subheader("📦 Packet Loss Analysis")

    loss_data = pd.DataFrame({

        "Host": [
            result["host"]
            for result in results
        ],

        "Packet Loss": [
            result["packet_loss"]
            for result in results
        ]

    })

    fig_loss = px.bar(
        loss_data,
        x="Host",
        y="Packet Loss",
        title="Packet Loss Percentage",
        text_auto=".1f"
    )

    fig_loss.update_layout(
        xaxis_title="Host",
        yaxis_title="Packet Loss (%)"
    )

    st.plotly_chart(
        fig_loss,
        use_container_width=True
    )


    # ==================================================
    # LATENCY HISTORY
    # ==================================================

    if st.session_state.history:

        st.subheader("📈 Monitoring History")

        history_df = pd.DataFrame(
            st.session_state.history
        )

        st.dataframe(
            history_df,
            use_container_width=True,
            hide_index=True
        )


    # ==================================================
    # TCP PORT MONITORING
    # ==================================================

    st.divider()

    st.subheader("🔌 TCP Port Monitoring")

    if st.button(
        f"Test {port_host}:{port}"
    ):

        port_result = check_port(
            port_host,
            port
        )

        if port_result["status"] == "Open":

            st.success(
                f"🟢 Port {port} is OPEN "
                f"on {port_host}"
            )

        elif port_result["status"] == "Closed":

            st.warning(
                f"🟡 Port {port} is CLOSED "
                f"on {port_host}"
            )

        else:

            st.error(
                "🔴 Unable to test the port."
            )

        if port_result["response"]:

            st.write(
                f"TCP response time: "
                f"**{port_result['response']:.2f} ms**"
            )


else:

    # ==================================================
    # INITIAL SCREEN
    # ==================================================

    st.info(
        "👈 Configure your hosts in the sidebar "
        "and click **Run Network Analysis**."
    )


# ==================================================
# FOOTER
# ==================================================

st.divider()

st.caption(
    "Cloud Network Monitoring System | "
    "Computer Networks Experiment 10 | Version 2"
)