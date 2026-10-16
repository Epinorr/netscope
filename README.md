# NetScope

**NetScope** is a Windows-first desktop utility for diagnosing common network connectivity problems, explaining likely causes, and running explicitly confirmed repair actions.

**Coded by EPINOR** · Version 1.1.0 · Python / PySide6 · MIT License

## Features

- Minimal dark desktop UI with diagnostic, repair, and report workspaces.
- Selectable diagnostic modules plus a full scan.
- Checks local adapter configuration, default gateway reachability, public IP reachability, DNS resolution, HTTPS, outbound TCP, proxy settings, VPN/tunnel indicators, Wi-Fi, routing table, system clock, and a short route trace.
- Heuristic findings explain patterns such as DNS failure while public IP reachability works.
- Repair center with confirmation dialogs, Windows UAC elevation for privileged actions, and post-repair verification for recommended repairs.
- TXT and JSON report export.
- App icon source and Windows ICO included.
- No automatic changes during scanning; no telemetry or report uploads.

## Repair behavior and safety

NetScope deliberately does not claim that every network fault can be repaired locally. Router WAN failures, ISP outages, network filtering, captive portals, remote service failures, and intentional security policies cannot always be fixed by an app on the PC.

The **Fix recommended issues** button only runs low-scope repairs that match the diagnostic results:

- **Flush DNS cache** — clears the local Windows resolver cache; it does not change DNS server settings.
- **Renew IP configuration** — asks DHCP for a fresh lease when no default gateway was detected; connectivity may pause briefly.

Additional repairs are available individually and require a confirmation dialog:

- **Reset WinHTTP proxy** — removes the system WinHTTP proxy. Do not run it if a managed network, VPN, or security product requires that proxy.
- **Reset Winsock catalog** — can affect VPN/security networking software and requires a Windows restart.
- **Reset TCP/IP stack** — may affect custom network settings and requires a Windows restart.

Privileged actions trigger Windows UAC. Read every confirmation. Advanced resets are intentionally excluded from one-click repair. After recommended repairs finish, NetScope reruns diagnostics to help verify the result. Administrator approval may be required.

## Requirements

- Windows 10/11 recommended.
- Python 3.10+ (64-bit recommended) to run from source.
- The diagnostic checks use Python's standard library and built-in Windows utilities; PySide6 provides the GUI.

## Run from source

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

If PowerShell blocks activation, use the virtual environment interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Build a standalone EXE

On Windows, double-click `Build-EXE.bat`, or run:

```powershell
py -m pip install -r requirements.txt
py -m PyInstaller --noconfirm --clean --windowed --name NetScope --onefile --icon "assets\netscope.ico" --add-data "assets;assets" --collect-all PySide6 main.py
```

Output: `dist\NetScope.exe`. Build on Windows for Windows. The bundled EXE will be comparatively large because it includes Python and Qt.

## Reading results

- **Gateway missing:** adapter, DHCP, or router configuration may be involved.
- **Gateway responds, public IP fails:** possible router WAN, ISP, firewall, VPN, or ICMP filtering issue.
- **Public IP works, DNS fails:** DNS settings, resolver failure, or filtering are stronger suspects.
- **DNS/IP work, HTTPS fails:** check proxy/VPN, system time, TLS inspection, captive portal, firewall, or endpoint-specific blocking.
- **Ping fails but HTTPS works:** ICMP may be blocked; do not reset networking based on ping alone.

These are heuristics, not proof. The app reports test evidence and uncertainty rather than treating every failed ping as a broken connection.

## Privacy

Reports can contain the computer name, local IP configuration, adapter names, Wi-Fi SSID, route table, and proxy details. Review and redact reports before posting them publicly. NetScope does not upload reports or send telemetry.

## Tests

```powershell
py -m unittest discover -s tests -v
```

## Contributing

Issues and pull requests are welcome. Include OS version, NetScope version, selected checks, and a redacted report when relevant. Do not publish sensitive network details unless you intend to disclose them.

## License

MIT. See [LICENSE](LICENSE).
