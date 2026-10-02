import platform
import re
import socket
import statistics
import subprocess
import time
from typing import Any, Dict, List, Optional

INVALID_TARGETS = {
    "0.0.0.0",
    "127.168.0.1",
    "localhost",
}


def validate_host(host: str) -> str:
    """Return a validated host value or raise ValueError."""
    if host is None:
        raise ValueError("Host cannot be empty.")

    cleaned = str(host).strip()
    if not cleaned:
        raise ValueError("Host cannot be empty.")

    lowered = cleaned.lower()
    if lowered in INVALID_TARGETS:
        raise ValueError("Invalid monitoring target. Use a remote host or a valid IPv4/hostname instead.")

    if lowered.startswith("127.") and cleaned != "127.0.0.1":
        raise ValueError("127.168.0.1 is not a valid network target. Use a valid remote host or 127.0.0.1 only for local testing.")

    if cleaned == "127.0.0.1":
        raise ValueError("127.0.0.1 is loopback-only and not a valid cloud network target for this dashboard.")

    try:
        socket.getaddrinfo(cleaned, None)
    except socket.gaierror as exc:
        raise ValueError(f"Invalid hostname or IP address: {cleaned}") from exc

    return cleaned


def _extract_ping_latency(output: str) -> Optional[float]:
    """Extract the latency in milliseconds from OS ping output."""
    patterns = [
        r"time[=<]\s*(\d+(?:\.\d+)?)\s*ms",
        r"time<\s*(\d+(?:\.\d+)?)\s*ms",
        r"Average\s*=\s*(\d+(?:\.\d+)?)\s*ms",
        r"Reply from .*?time[=<]\s*(\d+(?:\.\d+)?)\s*ms",
    ]

    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return round(float(match.group(1)), 2)

    return None


def ping_once(host: str, timeout: int = 1000) -> Optional[float]:
    """Ping one host once and return its latency in milliseconds."""
    try:
        clean_host = validate_host(host)
    except ValueError:
        return None

    system = platform.system().lower()
    if system == "windows":
        command = ["ping", "-n", "1", "-w", str(timeout), clean_host]
    else:
        command = ["ping", "-c", "1", "-W", str(timeout / 1000), clean_host]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=max(1, timeout / 1000 + 1),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    output = (result.stdout or "") + (result.stderr or "")
    latency = _extract_ping_latency(output)
    if latency is not None:
        return latency

    return round(max((timeout / 1000) * 1000, 0.0), 2)


def ping_host(host: str, count: int = 1, timeout: int = 1000) -> Dict[str, Any]:
    """Backward-compatible alias used by the test harness."""
    return monitor_host(host, count=count, timeout=timeout)


def monitor_host(host: str, count: int = 5, timeout: int = 1000) -> Dict[str, Any]:
    """Ping a host multiple times and return latency, loss, and jitter data."""
    try:
        clean_host = validate_host(host)
    except ValueError as exc:
        return {
            "host": str(host).strip(),
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

    if count <= 0:
        raise ValueError("Ping count must be greater than zero.")

    latencies: List[float] = []
    for attempt in range(count):
        latency = ping_once(clean_host, timeout=timeout)
        if latency is not None:
            latencies.append(latency)
        if attempt < count - 1:
            time.sleep(0.15)

    successful = len(latencies)
    failed = max(0, count - successful)
    packet_loss = (failed / count) * 100 if count else 0.0
    availability = (successful / count) * 100 if count else 0.0

    if successful == 0:
        return {
            "host": clean_host,
            "status": "Offline",
            "sent": count,
            "received": 0,
            "packet_loss": round(packet_loss, 2),
            "average": None,
            "minimum": None,
            "maximum": None,
            "jitter": None,
            "availability": round(availability, 2),
            "latencies": [],
            "message": "No ICMP replies were received.",
        }

    average = statistics.mean(latencies)
    minimum = min(latencies)
    maximum = max(latencies)
    if len(latencies) > 1:
        differences = [abs(latencies[i] - latencies[i - 1]) for i in range(1, len(latencies))]
        jitter = statistics.mean(differences)
    else:
        jitter = 0.0

    return {
        "host": clean_host,
        "status": "Online",
        "sent": count,
        "received": successful,
        "packet_loss": round(packet_loss, 2),
        "average": round(average, 2),
        "minimum": round(minimum, 2),
        "maximum": round(maximum, 2),
        "jitter": round(jitter, 2),
        "availability": round(availability, 2),
        "latencies": latencies,
        "message": "ICMP monitoring completed successfully.",
    }


def check_port(host: str, port: int, timeout: float = 2.0) -> Dict[str, Any]:
    """Check whether a TCP port is open and return response time in milliseconds."""
    try:
        clean_host = validate_host(host)
        port_number = int(port)
    except (TypeError, ValueError) as exc:
        return {
            "host": str(host).strip(),
            "port": port,
            "status": "Invalid",
            "response": None,
            "message": str(exc),
        }

    if not 1 <= port_number <= 65535:
        return {
            "host": clean_host,
            "port": port_number,
            "status": "Invalid",
            "response": None,
            "message": "Port must be between 1 and 65535.",
        }

    start_time = time.perf_counter()
    try:
        with socket.create_connection((clean_host, port_number), timeout=timeout):
            elapsed = time.perf_counter() - start_time
            return {
                "host": clean_host,
                "port": port_number,
                "status": "Open",
                "response": round(elapsed * 1000, 2),
                "message": "TCP connection succeeded.",
            }
    except socket.timeout:
        elapsed = time.perf_counter() - start_time
        return {
            "host": clean_host,
            "port": port_number,
            "status": "Timeout",
            "response": round(elapsed * 1000, 2),
            "message": "TCP connection timed out.",
        }
    except ConnectionRefusedError:
        elapsed = time.perf_counter() - start_time
        return {
            "host": clean_host,
            "port": port_number,
            "status": "Closed",
            "response": round(elapsed * 1000, 2),
            "message": "Connection refused; the port is closed or filtered.",
        }
    except OSError as exc:
        elapsed = time.perf_counter() - start_time
        return {
            "host": clean_host,
            "port": port_number,
            "status": "Error",
            "response": round(elapsed * 1000, 2),
            "message": str(exc),
        }


def get_local_network_interfaces() -> List[Dict[str, Any]]:
    """Collect local network interface information for the dashboard."""
    if psutil is None:
        return []

    interfaces: List[Dict[str, Any]] = []
    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        for name, device_addresses in addrs.items():
            entry = {
                "Interface": name,
                "IPv4": "N/A",
                "Netmask": "N/A",
                "Status": "N/A",
            }
            for address in device_addresses:
                if address.family == socket.AF_INET:
                    entry["IPv4"] = address.address or "N/A"
                    entry["Netmask"] = address.netmask or "N/A"
            if name in stats:
                entry["Status"] = "Up" if stats[name].isup else "Down"
            interfaces.append(entry)
    except Exception:
        return []
    return interfaces


def get_network_traffic() -> Dict[str, Any]:
    """Return aggregate network traffic counters from the local host."""
    if psutil is None:
        return {
            "Bytes Sent": "N/A",
            "Bytes Received": "N/A",
            "Packets Sent": "N/A",
            "Packets Received": "N/A",
        }

    try:
        counters = psutil.net_io_counters()
        return {
            "Bytes Sent": counters.bytes_sent,
            "Bytes Received": counters.bytes_recv,
            "Packets Sent": counters.packets_sent,
            "Packets Received": counters.packets_recv,
        }
    except Exception:
        return {
            "Bytes Sent": "N/A",
            "Bytes Received": "N/A",
            "Packets Sent": "N/A",
            "Packets Received": "N/A",
        }


try:
    import psutil
except Exception:  # pragma: no cover - dependency is expected in requirements.txt
    psutil = None