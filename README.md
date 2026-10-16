# 🌐 NetScope

[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)](#)
[![Platform](https://img.shields.io/badge/platform-Windows-0078d7.svg)](#)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**NetScope** is a Windows-first desktop utility designed for diagnosing common network connectivity problems, explaining likely causes through heuristic analysis, and running explicitly confirmed repair actions. 

Developed by **EPINOR**, it provides a local-first, safe approach to network troubleshooting.

---

## ✨ Key Features

* **Modern Dark Interface:** A minimal, dark desktop UI featuring dedicated workspaces for diagnostics, repairs, and reports.
* **Comprehensive Diagnostics:** Run selectable diagnostic modules or a full system scan. Checks include:
  * Local adapter configuration & Default gateway reachability.
  * Public IP reachability & DNS resolution.
  * HTTPS connectivity & Outbound TCP.
  * Proxy settings, VPN/tunnel indicators, Wi-Fi status, routing tables, system clock, and route tracing.
* **Heuristic Analysis:** Intelligent findings that explain complex patterns (e.g., identifying a DNS failure when public IP reachability is still active).
* **Safe Repair Center:** Executes scoped repairs with confirmation dialogs. Handles Windows UAC elevation for privileged actions and performs post-repair verification.
* **Flexible Export:** Export diagnostic reports in `TXT` or `JSON` formats.
* **Privacy-First:** Zero telemetry. NetScope makes no automatic changes during scanning and does not upload your reports.

---

## 🚀 Getting Started

### Requirements
* **OS:** Windows 10/11 (Recommended).
* **Environment:** Python 3.10+ (64-bit recommended).
* **Core Tech:** Standard Python library and built-in Windows utilities for diagnostics; `PySide6` for the GUI.

### Run from Source
Clone the repository and set up your virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
