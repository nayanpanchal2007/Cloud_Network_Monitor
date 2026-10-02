import subprocess
import platform
import time
import socket
import statistics


def ping_once(host):
    """
    Perform one ICMP ping.
    Returns latency in milliseconds or None if unsuccessful.
    """

    system = platform.system().lower()

    if system == "windows":
        command = [
            "ping",
            "-n",
            "1",
            "-w",
            "1000",
            host
        ]
    else:
        command = [
            "ping",
            "-c",
            "1",
            "-W",
            "1",
            host
        ]

    start_time = time.perf_counter()

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        end_time = time.perf_counter()

        if result.returncode == 0:
            latency = (end_time - start_time) * 1000
            return round(latency, 2)

        return None

    except Exception:
        return None


def monitor_host(host, count=5):
    """
    Perform multiple ping tests and calculate
    network performance statistics.
    """

    latencies = []

    for _ in range(count):

        latency = ping_once(host)

        if latency is not None:
            latencies.append(latency)

        time.sleep(0.15)

    successful = len(latencies)
    failed = count - successful

    if successful == 0:

        return {
            "host": host,
            "status": "Offline",
            "sent": count,
            "received": 0,
            "packet_loss": 100.0,
            "average": None,
            "minimum": None,
            "maximum": None,
            "jitter": None,
            "latencies": []
        }

    average = statistics.mean(latencies)
    minimum = min(latencies)
    maximum = max(latencies)

    # Mean absolute difference between consecutive
    # latency measurements
    if len(latencies) > 1:
        differences = [
            abs(latencies[i] - latencies[i - 1])
            for i in range(1, len(latencies))
        ]

        jitter = statistics.mean(differences)

    else:
        jitter = 0

    packet_loss = (failed / count) * 100

    return {
        "host": host,
        "status": "Online",
        "sent": count,
        "received": successful,
        "packet_loss": round(packet_loss, 2),
        "average": round(average, 2),
        "minimum": round(minimum, 2),
        "maximum": round(maximum, 2),
        "jitter": round(jitter, 2),
        "latencies": latencies
    }


def check_port(host, port):
    """
    Check whether a TCP port is reachable.
    """

    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    sock.settimeout(2)

    start_time = time.perf_counter()

    try:

        result = sock.connect_ex(
            (host, port)
        )

        end_time = time.perf_counter()

        response_time = round(
            (end_time - start_time) * 1000,
            2
        )

        if result == 0:

            return {
                "status": "Open",
                "response": response_time
            }

        return {
            "status": "Closed",
            "response": response_time
        }

    except Exception:

        return {
            "status": "Error",
            "response": None
        }

    finally:
        sock.close()