"""Conservative, explicit Windows network repair actions for NetScope."""
from __future__ import annotations

import ctypes
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FixSpec:
    id: str
    title: str
    description: str
    impact: str
    requires_admin: bool
    reboot: bool = False
    recommended: bool = False


FIXES = [
    FixSpec(
        "flush_dns",
        "Flush DNS cache",
        "Clears the local Windows DNS resolver cache so stale or poisoned domain records are refreshed.",
        "LOW",
        True,
        False,
        True,
    ),
    FixSpec(
        "arp_flush",
        "Clear ARP cache",
        "Removes stale IP-to-MAC address mappings on local interfaces. Helpful after router or switch changes.",
        "LOW",
        True,
        False,
        True,
    ),
    FixSpec(
        "renew_dhcp",
        "Renew IP configuration",
        "Requests a fresh IPv4 lease and gateway from the DHCP server. Network traffic may pause for a few seconds.",
        "MEDIUM",
        True,
        False,
        True,
    ),
    FixSpec(
        "reset_winhttp_proxy",
        "Reset WinHTTP proxy",
        "Clears system-level WinHTTP proxy settings. Do not use if your organization or security software mandates it.",
        "HIGH",
        True,
        False,
        False,
    ),
    FixSpec(
        "winsock_reset",
        "Reset Winsock catalog",
        "Rebuilds the Windows socket layer. Can affect VPN/firewall software and requires a system restart.",
        "HIGH",
        True,
        True,
        False,
    ),
    FixSpec(
        "tcpip_reset",
        "Reset TCP/IP stack",
        "Reinstalls core Windows TCP/IP registry parameters. May overwrite custom static configurations and requires a restart.",
        "HIGH",
        True,
        True,
        False,
    ),
]
FIX_BY_ID = {f.id: f for f in FIXES}


def is_windows() -> bool:
    return platform.system().lower() == "windows"


def is_admin() -> bool:
    if not is_windows():
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _command_for(fix_id: str) -> list[str]:
    commands = {
        "flush_dns": ["ipconfig", "/flushdns"],
        "arp_flush": ["netsh", "interface", "ip", "delete", "arpcache"],
        "renew_dhcp": ["ipconfig", "/renew"],
        "reset_winhttp_proxy": ["netsh", "winhttp", "reset", "proxy"],
        "winsock_reset": ["netsh", "winsock", "reset"],
        "tcpip_reset": [
            "netsh",
            "int",
            "ip",
            "reset",
            str(Path(tempfile.gettempdir()) / "NetScope-tcpip-reset.log"),
        ],
    }
    if fix_id not in commands:
        raise ValueError(f"Unknown repair action: {fix_id}")
    return commands[fix_id]


def _run_command(fix_id: str) -> dict:
    """Execute a known, allow-listed repair and return a serializable result."""
    if not is_windows():
        return {
            "ok": False,
            "fix_id": fix_id,
            "summary": "Repair actions are supported on Windows only.",
            "details": "",
        }
    spec = FIX_BY_ID.get(fix_id)
    if not spec:
        return {"ok": False, "fix_id": fix_id, "summary": "Unknown repair action.", "details": ""}
    try:
        proc = subprocess.run(
            _command_for(fix_id),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=75,
            shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        output = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
        ok = proc.returncode == 0
        return {
            "ok": ok,
            "fix_id": fix_id,
            "summary": "Command completed successfully." if ok else f"Command exited with code {proc.returncode}.",
            "details": output.strip() or "The command completed with no console output.",
            "returncode": proc.returncode,
            "reboot_required": bool(spec.reboot and ok),
        }
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "fix_id": fix_id, "summary": "The repair command timed out.", "details": str(exc)}
    except Exception as exc:
        return {"ok": False, "fix_id": fix_id, "summary": f"Repair failed: {type(exc).__name__}", "details": str(exc)}


def _launch_elevated_batch(fix_ids: list[str]) -> list[dict]:
    """Re-launch allow-listed actions in a single UAC prompt and collect their outputs."""
    if not is_windows():
        return [
            {"ok": False, "fix_id": fid, "summary": "Administrator elevation is only available on Windows.", "details": ""}
            for fid in fix_ids
        ]
    fd, output_name = tempfile.mkstemp(prefix="netscope-fix-", suffix=".json")
    os.close(fd)
    output_path = Path(output_name)
    joined_ids = ",".join(fix_ids)
    try:
        if getattr(sys, "frozen", False):
            executable = sys.executable
            child_args = ["--run-elevated-fix", joined_ids, "--result-file", str(output_path)]
        else:
            executable = sys.executable
            entry = Path(sys.argv[0]).resolve()
            child_args = [str(entry), "--run-elevated-fix", joined_ids, "--result-file", str(output_path)]
        params = subprocess.list2cmdline(child_args)
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, params, str(Path(sys.argv[0]).resolve().parent), 0
        )
        if ret <= 32:
            return [
                {
                    "ok": False,
                    "fix_id": fid,
                    "summary": "Administrator approval was declined or the elevated helper could not start.",
                    "details": f"ShellExecuteW status code: {ret}",
                }
                for fid in fix_ids
            ]
        deadline = time.monotonic() + (90 * max(1, len(fix_ids)))
        while time.monotonic() < deadline:
            if output_path.exists() and output_path.stat().st_size:
                try:
                    data = json.loads(output_path.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict):
                        return [data]
                except (OSError, json.JSONDecodeError):
                    pass
            time.sleep(0.25)
        return [
            {
                "ok": False,
                "fix_id": fid,
                "summary": "Timed out waiting for elevated repair process.",
                "details": "The UAC prompt may have expired or the helper process did not write results.",
            }
            for fid in fix_ids
        ]
    finally:
        try:
            output_path.unlink(missing_ok=True)
        except OSError:
            pass


def execute_fix(fix_id: str) -> dict:
    """Run a single repair action."""
    results = execute_fixes_batch([fix_id])
    return results[0] if results else {"ok": False, "fix_id": fix_id, "summary": "No repair executed.", "details": ""}


def execute_fixes_batch(fix_ids: list[str]) -> list[dict]:
    """Run one or more repair actions, grouping UAC elevation into a single prompt when needed."""
    valid_ids = [fid for fid in fix_ids if fid in FIX_BY_ID]
    if not valid_ids:
        return [{"ok": False, "fix_id": fid, "summary": "Unknown repair action.", "details": ""} for fid in fix_ids]
    if not is_windows():
        return [
            {"ok": False, "fix_id": fid, "summary": "Repair actions are supported on Windows only.", "details": ""}
            for fid in valid_ids
        ]
    needs_elevation = any(FIX_BY_ID[fid].requires_admin for fid in valid_ids) and not is_admin()
    if needs_elevation:
        return _launch_elevated_batch(valid_ids)

    outputs = []
    for fid in valid_ids:
        spec = FIX_BY_ID[fid]
        res = _run_command(fid)
        res["reboot_required"] = bool(spec.reboot and res.get("ok"))
        outputs.append(res)
    return outputs


def execute_elevated_from_cli(fix_ids: list[str] | str, output_path: str) -> int:
    """Entry point for the UAC child process. Never accepts arbitrary shell commands."""
    if isinstance(fix_ids, str):
        fix_ids = [fid.strip() for fid in fix_ids.split(",") if fid.strip()]
    results = [_run_command(fid) for fid in fix_ids if fid in FIX_BY_ID]
    try:
        payload = results[0] if len(results) == 1 else results
        Path(output_path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except OSError:
        return 2
    return 0 if all(r.get("ok") for r in results) else 1


def analyse_results(results: list) -> list[dict]:
    """Return concise, heuristic findings; wording deliberately avoids certainty."""
    by_id = {getattr(r, "id", r.get("id") if isinstance(r, dict) else None): r for r in results}

    def status(cid: str) -> str | None:
        item = by_id.get(cid)
        return getattr(item, "status", item.get("status") if isinstance(item, dict) else None)

    findings = []
    gateway, public_ip, dns, https, tcp, proxy = (
        status(x) for x in ("gateway", "internet_ip", "dns", "https", "tcp", "proxy")
    )

    if gateway == "FAIL":
        findings.append({
            "level": "critical",
            "title": "No default gateway",
            "detail": "The system has no active route to a local router. Check Wi-Fi/Ethernet connection or renew DHCP.",
            "fixes": ["renew_dhcp", "arp_flush"],
        })
    elif gateway == "WARN":
        findings.append({
            "level": "warning",
            "title": "Gateway ping did not reply",
            "detail": "Some routers drop ICMP pings by default. If external checks pass, this is harmless; otherwise clear ARP or renew DHCP.",
            "fixes": ["arp_flush"] if public_ip == "FAIL" else [],
        })

    if public_ip == "FAIL" and gateway in ("PASS", "WARN") and https != "PASS" and tcp != "PASS":
        findings.append({
            "level": "critical",
            "title": "Public IP reachability failed",
            "detail": "Local gateway is configured, but external IP packets cannot reach the internet. Router WAN, ISP outage, or firewall rules may be responsible.",
            "fixes": ["renew_dhcp", "arp_flush"] if gateway == "WARN" else [],
        })
    elif public_ip == "FAIL" and (https == "PASS" or tcp == "PASS"):
        findings.append({
            "level": "info",
            "title": "Ping may be blocked",
            "detail": "ICMP ping failed, but HTTPS/TCP connectivity succeeded. Your network or ISP likely filters ICMP; internet access is working.",
            "fixes": [],
        })

    if dns == "FAIL":
        detail = "Hostname lookup failed for the tested domains. A resolver issue, VPN/proxy filtering, or network policy may be responsible."
        if public_ip == "PASS":
            detail += " Public IP reachability works, which makes DNS a stronger suspect."
        findings.append({
            "level": "critical",
            "title": "DNS lookup failed",
            "detail": detail,
            "fixes": ["flush_dns"],
        })
    elif dns == "WARN":
        findings.append({
            "level": "warning",
            "title": "Partial DNS resolution",
            "detail": "Some domains resolved while others failed. Flushing DNS cache may clear stale negative records.",
            "fixes": ["flush_dns"],
        })

    if https == "FAIL" and public_ip == "PASS":
        detail = "IP reachability works, but HTTPS requests failed. Check proxy/VPN settings, system clock, captive portals, or firewall filtering."
        fixes = ["reset_winhttp_proxy"] if proxy == "WARN" else []
        findings.append({
            "level": "critical",
            "title": "HTTPS requests failed",
            "detail": detail,
            "fixes": fixes,
        })
    elif https == "WARN":
        findings.append({
            "level": "warning",
            "title": "HTTPS warning or captive portal suspected",
            "detail": "One or more HTTP/HTTPS probes failed or redirected. If on public Wi-Fi, open a browser to sign in to the captive portal.",
            "fixes": [],
        })

    if tcp == "FAIL" and gateway == "PASS":
        findings.append({
            "level": "warning",
            "title": "Outbound TCP connections failed",
            "detail": "Direct TCP connections on port 443/53 were blocked. Inspect firewall rules, VPN kill-switches, or proxy configurations.",
            "fixes": [],
        })

    if proxy == "WARN" and https == "FAIL":
        findings.append({
            "level": "warning",
            "title": "Proxy settings need review",
            "detail": "Active proxy configuration was detected while HTTPS failed. Verify whether a VPN or proxy client left behind an inactive proxy port.",
            "fixes": [],
        })

    if not findings:
        if any(status(x) == "FAIL" for x in ("gateway", "internet_ip", "dns", "https", "tcp")):
            findings.append({
                "level": "warning",
                "title": "Review failed checks",
                "detail": "Failures did not match a standard pattern. Inspect individual check details before applying advanced repairs.",
                "fixes": [],
            })
        elif results:
            findings.append({
                "level": "success",
                "title": "No clear connectivity fault detected",
                "detail": "All core network layers (Gateway, IP, DNS, TCP, and HTTPS) responded normally.",
                "fixes": [],
            })
    return findings


def recommended_fixes(results: list) -> list[str]:
    """Choose only scoped, low-risk repairs with a direct relationship to test findings."""
    by_id = {getattr(r, "id", r.get("id") if isinstance(r, dict) else None): r for r in results}

    def status(cid: str) -> str | None:
        item = by_id.get(cid)
        return getattr(item, "status", item.get("status") if isinstance(item, dict) else None)

    selected = []
    if status("dns") == "FAIL":
        selected.append("flush_dns")
    if status("gateway") == "FAIL":
        selected.append("renew_dhcp")
    # Preserve stable ordering and never include high-impact resets in one-click repair.
    return list(dict.fromkeys(selected))