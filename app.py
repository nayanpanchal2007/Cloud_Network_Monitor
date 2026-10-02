import streamlit as st
import pandas as pd
import plotly.express as px
from network_monitor import ping_host
from datetime import datetime

# --------------------------------------------------
# Page Configuration
# --------------------------------------------------

st.set_page_config(
    page_title="Cloud Network Monitor",
    page_icon="🌐",
    layout="wide"
)

# --------------------------------------------------
# Custom CSS
# --------------------------------------------------

st.markdown("""
<style>
    .main-title {
        font-size: 40px;
        font-weight: 700;
        margin-bottom: 0;
    }

    .subtitle {
        font-size: 18px;
        color: #666;
        margin-bottom: 25px;
    }

    .status-online {
        color: #16a34a;
        font-weight: bold;
    }

    .status-offline {
        color: #dc2626;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Header
# --------------------------------------------------

st.markdown(
    '<div class="main-title">🌐 Cloud Network Monitoring System</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Real-time network connectivity and performance monitoring dashboard'
    '</div>',
    unsafe_allow_html=True
)

# --------------------------------------------------
# Sidebar
# --------------------------------------------------

st.sidebar.title("⚙️ Monitoring Settings")

target = st.sidebar.text_input(
    "Target Host",
    value="8.8.8.8"
)

if st.sidebar.button("🔍 Check Network"):
    st.session_state["run_check"] = True

# --------------------------------------------------
# Perform Network Check
# --------------------------------------------------

if "run_check" not in st.session_state:
    st.session_state["run_check"] = False

if st.session_state["run_check"]:

    result = ping_host(target)

    # Store result
    current_time = datetime.now().strftime("%H:%M:%S")

    history = st.session_state.get("history", [])

    history.append({
        "Time": current_time,
        "Host": target,
        "Latency": result["latency"],
        "Status": result["status"]
    })

    st.session_state["history"] = history

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    if result["status"] == "Online":
        status_text = "🟢 Online"
    else:
        status_text = "🔴 Offline"

    latency = result["latency"]

    if latency is not None:
        latency_text = f"{latency} ms"
    else:
        latency_text = "N/A"

    # --------------------------------------------------
    # Metrics
    # --------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Network Status",
            status_text
        )

    with col2:
        st.metric(
            "Response Time",
            latency_text
        )

    with col3:
        online_count = sum(
            1 for item in history
            if item["Status"] == "Online"
        )

        st.metric(
            "Successful Checks",
            online_count
        )

    with col4:
        total_checks = len(history)

        if total_checks > 0:
            availability = (
                online_count / total_checks
            ) * 100
        else:
            availability = 0

        st.metric(
            "Availability",
            f"{availability:.1f}%"
        )

    st.divider()

    # --------------------------------------------------
    # History Table
    # --------------------------------------------------

    df = pd.DataFrame(history)

    st.subheader("📊 Network Monitoring History")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------
    # Latency Graph
    # --------------------------------------------------

    valid_df = df.dropna(subset=["Latency"])

    if not valid_df.empty:

        st.subheader("📈 Latency History")

        fig = px.line(
            valid_df,
            x="Time",
            y="Latency",
            markers=True,
            title="Network Response Time"
        )

        fig.update_layout(
            xaxis_title="Time",
            yaxis_title="Latency (ms)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

else:

    st.info(
        "Enter a host address and click "
        "**Check Network** to start monitoring."
    )

# --------------------------------------------------
# Footer
# --------------------------------------------------

st.divider()

st.caption(
    "Cloud Network Monitoring System | "
    "Computer Networks Experiment 10"
)