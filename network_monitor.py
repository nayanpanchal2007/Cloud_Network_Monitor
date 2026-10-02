import subprocess
import platform
import time
import socket


def ping_host(host):
    """
    Ping a host and return status and response time.
    """

    system = platform.system().lower()

    if system == "windows":
        command = ["ping", "-n", "1", "-w", "1000", host]
    else:
        command = ["ping", "-c", "1", "-W", "1", host]

    start_time = time.time()

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        end_time = time.time()

        if result.returncode == 0:
            latency = round((end_time - start_time) * 1000, 2)

            return {
                "host": host,
                "status": "Online",
                "latency": latency
            }

        return {
            "host": host,
            "status": "Offline",
            "latency": None
        }

    except Exception:
        return {
            "host": host,
            "status": "Error",
            "latency": None
        }


def check_port(host, port):
    """
    Check whether a TCP port is reachable.
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)

    try:
        result = sock.connect_ex((host, port))

        if result == 0:
            return "Open"

        return "Closed"

    except Exception:
        return "Error"

    finally:
        sock.close()