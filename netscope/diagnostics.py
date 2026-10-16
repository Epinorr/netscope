from __future__ import annotations

import datetime
import json
import os
import platform
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Callable


@dataclass
class CheckResult:
    id: str
    title: str
    status: str  # PASS, WARN, FAIL, INFO, SKIP
    summary: str
    details: str = ""
    duration_ms: int = 0
    remediation: str = ""


@dataclass
class DiagnosticReport:
    generated_at: str
    hostname: str
    platform: str
    summary: dict
    results: list
    system_info: dict


def _run(cmd: list[str], timeout: int = 12) -> tuple[int, str]:
    """Run a diagnostic command without a shell; return exit code and combined output."""
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            errors="replace",
            shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
        return p.returncode, out.strip()
    except FileNotFoundError:
        return 127, f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"Timed out after {timeout}s: {' '.join(cmd)}"
    except Exception as exc:
        return 1, f"{type(exc).__name__}: {exc}"


def _ping(host: str, count: int = 2, timeout: int = 3) -> tuple[int, str]:
    if platform.system().lower() == "windows":
        return _run(["ping", "-n", str(count), "-w", str(timeout * 1000), host], timeout=timeout * count + 3)
    return _run(["ping", "-c", str(count), "-W", str(timeout), host], timeout=timeout * count + 3)


def _extract_ping_ms(output: str) -> str | None:
    """Extract average or single latency in ms from ping output."""
    avg_match = re.search(r"Average\s*=\s*(\d+)\s*ms", output, re.I)
    if avg_match:
        return f"{avg_match.group(1)} ms"
    time_match = re.search(r"time[=<](\d+(?:\.\d+)?)\s*ms", output, re.I)
    if time_match:
        return f"{time_match.group(1)} ms"
    return None


def _has_reply(output: str) -> bool:
    if platform.system().lower() == "windows":
        if "destination host unreachable" in output.lower():
            return False
        return bool(re.search(r"Received\s*=\s*[1-9]|Reply from .*bytes=", output, re.I))
    return bool(re.search(r"\b[1-9]\d*\s+(?:packets )?received|bytes from", output, re.I))


def _result(
    check_id: str,
    title: str,
    status: str,
    summary: str,
    details: str = "",
    start: float | None = None,
    remediation: str = "",
) -> CheckResult:
    ms = int((time.monotonic() - start) * 1000) if start else 0
    return CheckResult(check_id, title, status, summary, details.strip(), ms, remediation)


def run_check(check_id: str, progress: Callable[[str], None] | None = None) -> CheckResult:
    start = time.monotonic()

    if check_id == "system":
        info = {
            "OS": platform.platform(),
            "Architecture": platform.architecture()[0],
            "Python": platform.python_version(),
            "Hostname": socket.gethostname(),
            "User": os.environ.get("USERNAME") or os.environ.get("USER") or "Unknown",
        }
        return _result(
            check_id,
            "System information",
            "INFO",
            f"{platform.system()} {platform.release()} ({info['Architecture']})",
            json.dumps(info, indent=2),
            start,
        )

    if check_id == "interfaces":
        cmd = ["ipconfig", "/all"] if platform.system().lower() == "windows" else ["ip", "address"]
        code, out = _run(cmd)
        has_ipv4 = bool(re.search(r"(?:IPv4 Address|inet )[^\r\n]*?(\d+\.\d+\.\d+\.\d+)", out, re.I))
        status = "PASS" if (code == 0 and has_ipv4) else "WARN"
        summary = "Active IPv4 configuration detected" if status == "PASS" else "No active IPv4 address found on adapters"
        return _result(
            check_id,
            "Network adapters",
            status,
            summary,
            out,
            start,
            "Verify that your Wi-Fi or Ethernet adapter is enabled and connected.",
        )

    if check_id == "gateway":
        if platform.system().lower() == "windows":
            _, out = _run(["ipconfig"])
            gateways = [
                g.strip()
                for g in re.findall(r"Default Gateway[ .]*:\s*([0-9a-fA-F:.]+)", out, re.I)
                if g.strip() and g.strip() != "0.0.0.0"
            ]
            if not gateways:
                _, route = _run(["route", "print", "-4"])
                m = re.search(r"^\s*0\.0\.0\.0\s+0\.0\.0\.0\s+([0-9.]+)", route, re.M)
                gateways = [m.group(1)] if m else []
            if not gateways:
                return _result(
                    check_id,
                    "Default gateway",
                    "FAIL",
                    "No default gateway detected",
                    out,
                    start,
                    "Reconnect Wi-Fi/Ethernet, renew DHCP lease, or check router power and cables.",
                )
            gateway = next((g for g in gateways if "." in g), gateways[0])
        else:
            _, out = _run(["ip", "route", "show", "default"])
            m = re.search(r"default via (\S+)", out)
            gateway = m.group(1) if m else ""
            if not gateway:
                return _result(
                    check_id,
                    "Default gateway",
                    "FAIL",
                    "No default gateway detected",
                    out,
                    start,
                    "Check your local network connection and router DHCP status.",
                )

        _, ping_out = _ping(gateway, count=2, timeout=2)
        ok = _has_reply(ping_out)
        latency = _extract_ping_ms(ping_out)
        lat_str = f" ({latency})" if latency else ""
        return _result(
            check_id,
            "Default gateway",
            "PASS" if ok else "WARN",
            f"Gateway {gateway} reachable{lat_str}" if ok else f"Gateway {gateway} did not reply to ICMP",
            f"Detected Gateway: {gateway}\n\n{ping_out}",
            start,
            "Some routers drop ICMP ping by policy. If internet works, ignore this warning; otherwise flush ARP or renew DHCP.",
        )

    if check_id == "internet_ip":
        targets = [("Cloudflare", "1.1.1.1"), ("Google", "8.8.8.8")]
        logs = []
        best_latency = None
        any_ok = False
        for label, ip in targets:
            _, out = _ping(ip, count=2, timeout=3)
            ok = _has_reply(out)
            logs.append(f"=== {label} ({ip}) ===\n{out}")
            if ok:
                any_ok = True
                best_latency = best_latency or _extract_ping_ms(out)
                break
        lat_str = f" ({best_latency})" if best_latency else ""
        return _result(
            check_id,
            "Internet reachability (IP)",
            "PASS" if any_ok else "FAIL",
            f"Public IP reachable{lat_str}" if any_ok else "Could not ping 1.1.1.1 or 8.8.8.8",
            "\n\n".join(logs),
            start,
            "If gateway works but public IP fails, check router WAN connection, ISP status, or firewall ICMP rules.",
        )

    if check_id == "dns":
        domains = ["cloudflare.com", "google.com", "microsoft.com"]
        outcomes = []
        detail = []
        t0 = time.monotonic()
        for host in domains:
            try:
                ips = sorted({x[4][0] for x in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
                outcomes.append(True)
                detail.append(f"[OK] {host} -> {', '.join(ips[:4])}")
            except Exception as exc:
                outcomes.append(False)
                detail.append(f"[FAIL] {host} -> {type(exc).__name__}: {exc}")
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        ok = any(outcomes)
        status = "PASS" if all(outcomes) else ("WARN" if ok else "FAIL")
        summary = (
            f"All test domains resolved ({elapsed_ms} ms)"
            if all(outcomes)
            else ("Partial DNS resolution failure" if ok else "DNS resolution failed completely")
        )
        return _result(
            check_id,
            "DNS resolution",
            status,
            summary,
            "\n".join(detail),
            start,
            "Flush the DNS cache or verify custom DNS server settings on your adapter/router.",
        )

    if check_id == "https":
        targets = [
            ("Cloudflare Trace", "https://www.cloudflare.com/cdn-cgi/trace"),
            ("Google 204", "https://www.google.com/generate_204"),
            ("Microsoft ConnectTest", "http://www.msftconnecttest.com/connecttest.txt"),
        ]
        details = []
        passed = []
        captive_suspected = False
        for name, url in targets:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "NetScope/1.2"})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    final_url = resp.geturl()
                    redirected = final_url != url and not final_url.startswith(url)
                    if name == "Microsoft ConnectTest" and redirected:
                        captive_suspected = True
                    details.append(f"[HTTP {resp.status}] {name}: {url}" + (f" -> Redirected to {final_url}" if redirected else ""))
                    passed.append(200 <= resp.status < 400 and not redirected)
            except Exception as exc:
                details.append(f"[FAIL] {name} ({url}): {type(exc).__name__}: {exc}")
                passed.append(False)

        if captive_suspected:
            status = "WARN"
            summary = "Captive portal or HTTP redirect detected"
        else:
            status = "PASS" if all(passed[:2]) else ("WARN" if any(passed) else "FAIL")
            summary = (
                "HTTPS connectivity verified"
                if status == "PASS"
                else ("Some web endpoints failed or redirected" if status == "WARN" else "All HTTPS requests failed")
            )
        return _result(
            check_id,
            "HTTPS connectivity",
            status,
            summary,
            "\n".join(details),
            start,
            "Check proxy/VPN settings, system clock accuracy, captive portal login page, or firewall rules.",
        )

    if check_id == "tcp":
        tests = [
            ("Cloudflare (443)", "1.1.1.1", 443),
            ("Google DNS (53)", "8.8.8.8", 53),
        ]
        details = []
        passed = []
        for name, host, port in tests:
            t_conn = time.monotonic()
            try:
                with socket.create_connection((host, port), timeout=4):
                    ms = int((time.monotonic() - t_conn) * 1000)
                    details.append(f"[CONNECTED] {name} ({host}:{port}) in {ms} ms")
                    passed.append(True)
            except Exception as exc:
                details.append(f"[FAILED] {name} ({host}:{port}): {type(exc).__name__}: {exc}")
                passed.append(False)
        status = "PASS" if all(passed) else ("WARN" if any(passed) else "FAIL")
        return _result(
            check_id,
            "Outbound TCP",
            status,
            "Direct TCP sockets succeeded" if all(passed) else ("Partial TCP port reachability" if any(passed) else "Outbound TCP connections blocked"),
            "\n".join(details),
            start,
            "Check outbound firewall rules, proxy policies, VPN kill-switches, or ISP port filtering.",
        )

    if check_id == "proxy":
        env_proxy = {k: v for k, v in os.environ.items() if "proxy" in k.lower() and v}
        try:
            system_proxy = urllib.request.getproxies()
        except Exception as exc:
            system_proxy = {"error": str(exc)}
        details = (
            "Environment proxy variables:\n"
            + (json.dumps(env_proxy, indent=2) if env_proxy else "(none)")
            + "\n\nSystem proxy configuration:\n"
            + (json.dumps(system_proxy, indent=2) if system_proxy else "(none)")
        )
        configured = bool(env_proxy or system_proxy)
        return _result(
            check_id,
            "Proxy configuration",
            "WARN" if configured else "INFO",
            "Active proxy configuration detected" if configured else "No proxy configuration active",
            details,
            start,
            "If you are not using a proxy or VPN, a leftover proxy entry can block web traffic. Disable it in Windows Proxy Settings.",
        )

    if check_id == "vpn":
        if platform.system().lower() == "windows":
            _, out = _run(["ipconfig", "/all"])
            _, route = _run(["route", "print"])
            detail = out + "\n\nROUTES\n" + route
            matches = re.findall(r"(?im)^.*(?:VPN|WireGuard|TAP|TUN|Tunnel|OpenVPN|Wintun|ZeroTier|Tailscale|Cisco AnyConnect).*$", detail)
        else:
            _, out = _run(["ip", "link"])
            _, route = _run(["ip", "route"])
            detail = out + "\n" + route
            matches = re.findall(r"(?im)^.*(?:tun|tap|wg|vpn|tailscale|zt).*$", detail)
        clean_matches = list(dict.fromkeys(m.strip() for m in matches if m.strip()))
        return _result(
            check_id,
            "VPN / tunnel indicators",
            "INFO",
            f"Found {len(clean_matches)} tunnel/VPN indicator(s)" if clean_matches else "No active VPN/tunnel indicators detected",
            "\n".join(clean_matches[:60]) if clean_matches else "No virtual tunnel interfaces matched standard patterns.",
            start,
            "If experiencing routing or DNS issues, test after disconnecting VPN software.",
        )

    if check_id == "wifi":
        if platform.system().lower() != "windows":
            return _result(check_id, "Wi-Fi status", "SKIP", "Wi-Fi inspection is Windows-only", "", start)
        code, out = _run(["netsh", "wlan", "show", "interfaces"])
        if code != 0:
            return _result(
                check_id,
                "Wi-Fi status",
                "INFO",
                "No wireless interface or WLAN service inactive",
                out,
                start,
                "If using Ethernet, ignore this. For Wi-Fi, ensure the WLAN AutoConfig service is running.",
            )
        state = re.search(r"^\s*State\s*:\s*(.+)$", out, re.M | re.I)
        ssid = re.search(r"^\s*SSID\s*:\s*(.+)$", out, re.M | re.I)
        signal = re.search(r"^\s*Signal\s*:\s*(.+)$", out, re.M | re.I)
        connected = bool(state and "connected" in state.group(1).lower() and "disconnected" not in state.group(1).lower())
        sig_str = f" ({signal.group(1).strip()})" if signal else ""
        return _result(
            check_id,
            "Wi-Fi status",
            "PASS" if connected else "INFO",
            f"Connected to {ssid.group(1).strip() if ssid else 'Wi-Fi'}{sig_str}" if connected else "Wi-Fi adapter is not connected",
            out,
            start,
            "Check signal strength and channel congestion if wireless speed or stability is poor.",
        )

    if check_id == "routes":
        cmd = ["route", "print", "-4"] if platform.system().lower() == "windows" else ["ip", "route"]
        code, out = _run(cmd)
        return _result(
            check_id,
            "Routing table",
            "PASS" if code == 0 else "WARN",
            "IPv4 routing table collected" if code == 0 else "Could not read routing table",
            out,
            start,
            "Review default routes (0.0.0.0) if traffic is being misdirected by a stuck VPN adapter.",
        )

    if check_id == "system_time":
        now = datetime.datetime.now().astimezone()
        return _result(
            check_id,
            "System clock",
            "INFO",
            f"Local time: {now:%Y-%m-%d %H:%M:%S} ({now.strftime('%z')})",
            f"ISO Timestamp: {now.isoformat()}\nTimezone: {now.tzname()}",
            start,
            "Ensure system date and time are synced; skewed clocks cause TLS/HTTPS certificate errors.",
        )

    if check_id == "traceroute":
        if platform.system().lower() == "windows":
            cmd = ["tracert", "-d", "-h", "8", "-w", "600", "1.1.1.1"]
        else:
            cmd = ["traceroute", "-n", "-m", "8", "-w", "1", "1.1.1.1"]
        code, out = _run(cmd, timeout=18)
        return _result(
            check_id,
            "Route trace",
            "INFO" if code == 0 else "WARN",
            "8-hop trace to 1.1.1.1 completed" if code == 0 else "Route trace timed out or failed",
            out,
            start,
            "Intermediate hops showing '*' simply ignore ICMP time-exceeded packets and do not indicate a fault.",
        )

    return _result(check_id, check_id, "SKIP", "Unknown diagnostic check", "", start)


CHECKS = [
    ("system", "System information", "OS version, architecture, and host environment"),
    ("interfaces", "Network adapters", "IPv4/IPv6 addresses, DNS servers, and DHCP state"),
    ("gateway", "Default gateway", "Local router detection and ICMP latency test"),
    ("internet_ip", "Internet reachability (IP)", "Direct ICMP ping to 1.1.1.1 / 8.8.8.8 without DNS"),
    ("dns", "DNS resolution", "Resolves multiple global domains via system resolver"),
    ("https", "HTTPS connectivity", "Tests TLS handshakes, HTTP status, and captive portals"),
    ("tcp", "Outbound TCP", "Tests raw TCP socket connections on ports 443 and 53"),
    ("proxy", "Proxy configuration", "Detects environment and Windows WinINET proxy rules"),
    ("vpn", "VPN / tunnel indicators", "Scans for virtual tunnel adapters and VPN routes"),
    ("wifi", "Wi-Fi status", "Wireless interface state, SSID, and signal quality"),
    ("routes", "Routing table", "Inspects active IPv4 routing table entries"),
    ("system_time", "System clock", "Verifies local clock and UTC offset for TLS validity"),
    ("traceroute", "Route trace", "Maps the first 8 network hops toward Cloudflare"),
]


def redact_sensitive_text(text: str) -> str:
    """Redact private IPs, MAC addresses, SSIDs, hostnames, and usernames for safe sharing."""
    if not text:
        return text
    hostname = socket.gethostname()
    username = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    out = text
    if hostname and len(hostname) > 2:
        out = re.sub(re.escape(hostname), "[REDACTED-HOST]", out, flags=re.I)
    if username and len(username) > 2:
        out = re.sub(re.escape(username), "[REDACTED-USER]", out, flags=re.I)
    # Redact MAC addresses
    out = re.sub(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b", "[REDACTED-MAC]", out)
    # Redact SSID / BSSID lines
    out = re.sub(r"(?im)^(\s*B?SSID\s*:\s*)(.+)$", r"\1[REDACTED-SSID]", out)
    # Redact private IPv4 ranges (10.x.x.x, 192.168.x.x, 172.16-31.x.x)
    out = re.sub(
        r"\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})\b",
        "[PRIVATE-IP]",
        out,
    )
    return out


def build_report(results: list[CheckResult]) -> DiagnosticReport:
    counts = {s: sum(1 for r in results if r.status == s) for s in ("PASS", "WARN", "FAIL", "INFO", "SKIP")}
    return DiagnosticReport(
        datetime.datetime.now().astimezone().isoformat(),
        socket.gethostname(),
        platform.platform(),
        counts,
        [asdict(r) for r in results],
        {"python": platform.python_version(), "architecture": platform.architecture()[0]},
    )


def report_as_text(report: DiagnosticReport, redact: bool = False) -> str:
    lines = [
        "NETSCOPE NETWORK DIAGNOSTICS REPORT",
        "=" * 42,
        f"Generated : {report.generated_at}",
        f"Host      : {report.hostname}",
        f"Platform  : {report.platform}",
        "",
        "SUMMARY",
        "-" * 42,
    ]
    lines += [f"{k:<8}: {v}" for k, v in report.summary.items()]
    lines += ["", "CHECK RESULTS", "-" * 42]
    for r in report.results:
        lines += [
            f"[{r['status']}] {r['title']} ({r.get('duration_ms', 0)} ms)",
            f"Summary: {r['summary']}",
        ]
        if r.get("details"):
            lines += ["Details:", r["details"]]
        if r.get("remediation"):
            lines += ["Suggested next step: " + r["remediation"]]
        lines.append("")
    lines += [
        "PRIVACY NOTE",
        "-" * 42,
        "This report may contain hostname, SSID, local IP addresses, adapter details, routes, and proxy settings.",
        "Enable 'Redact private details' or review manually before sharing publicly.",
    ]
    output = "\n".join(lines)
    return redact_sensitive_text(output) if redact else output