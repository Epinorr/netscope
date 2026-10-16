from __future__ import annotations

import datetime
import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .diagnostics import CHECKS, build_report, redact_sensitive_text, report_as_text, run_check
from .repairs import (
    FIX_BY_ID,
    FIXES,
    analyse_results,
    execute_fixes_batch,
    is_admin,
    is_windows,
    recommended_fixes,
)

APP_NAME = "NetScope"
APP_VERSION = __version__

STYLE = r"""
* { font-family: "Segoe UI Variable Display", "Segoe UI", "Inter", "Arial"; font-size: 10pt; }
QMainWindow, QWidget { background: #070a10; color: #e6edf7; }
QWidget#Sidebar { background: #0a0f18; border-right: 1px solid #182232; }
QFrame#BrandMark {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1d335c, stop:1 #101e38);
    border: 1px solid #2e4d82;
    border-radius: 12px;
}
QLabel#Brand { color: #ffffff; font-size: 16pt; font-weight: 800; letter-spacing: 0.3px; }
QLabel#BrandSub { color: #647896; font-size: 7.5pt; font-weight: 700; letter-spacing: 1.2px; }
QLabel#FooterBrand { color: #94a6c2; font-size: 9pt; font-weight: 600; }
QLabel#PageTitle { color: #f8fafc; font-size: 21pt; font-weight: 750; }
QLabel#SectionTitle { color: #f1f5f9; font-size: 10.5pt; font-weight: 700; }
QLabel#Muted { color: #8798b0; font-size: 9.5pt; }
QLabel#Tiny { color: #697b96; font-size: 8pt; font-weight: 600; }
QLabel#MetricValue { color: #ffffff; font-size: 22pt; font-weight: 800; }
QLabel#HeroStatus { color: #ffffff; font-size: 15pt; font-weight: 750; }
QLabel#Pill {
    color: #9dc0ff;
    background: #122038;
    border: 1px solid #25406b;
    border-radius: 9px;
    padding: 4px 10px;
    font-size: 8pt;
    font-weight: 750;
}
QFrame#Surface { background: #0d131f; border: 1px solid #1a2639; border-radius: 14px; }
QFrame#SurfaceSoft { background: #0b101b; border: 1px solid #172234; border-radius: 11px; }
QFrame#SurfaceSoft:hover { background: #0f1726; border: 1px solid #283c5c; }
QFrame#Hero {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f1b2e, stop:1 #0c1422);
    border: 1px solid #233a5e;
    border-radius: 15px;
}
QFrame#AccentMark { background: #3b82f6; border-radius: 2px; }
QPushButton {
    color: #dce6f5;
    background: #131c2b;
    border: 1px solid #23324a;
    border-radius: 9px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover { background: #1a273d; border-color: #365078; color: #ffffff; }
QPushButton:pressed { background: #111927; }
QPushButton:disabled { color: #4a5970; background: #0c121c; border-color: #162030; }
QPushButton#Primary {
    color: #ffffff;
    background: #3b82f6;
    border: 1px solid #4f8ff7;
    font-weight: 700;
}
QPushButton#Primary:hover { background: #2563eb; border-color: #60a5fa; }
QPushButton#Primary:disabled { background: #17253d; border-color: #1f3252; color: #597196; }
QPushButton#NavButton {
    text-align: left;
    padding: 11px 14px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 10px;
    color: #8b9db7;
    font-weight: 600;
}
QPushButton#NavButton:hover { background: #111927; color: #e2ecf9; }
QPushButton#NavButton:checked {
    color: #ffffff;
    background: #142238;
    border: 1px solid #294673;
    font-weight: 700;
}
QPushButton#Danger { color: #fda4af; background: #24131a; border: 1px solid #4c2331; }
QPushButton#Danger:hover { background: #361a24; border-color: #703044; color: #ffe4e6; }
QCheckBox { color: #dce6f5; spacing: 8px; }
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #384963;
    border-radius: 5px;
    background: #090e17;
}
QCheckBox::indicator:hover { border-color: #5b85c7; }
QCheckBox::indicator:checked { background: #3b82f6; border: 1px solid #60a5fa; }
QScrollArea { border: none; background: transparent; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item {
    background: #0a101a;
    border: 1px solid #182336;
    border-radius: 9px;
    padding: 10px 12px;
    margin-bottom: 6px;
}
QListWidget::item:selected { background: #13223a; border: 1px solid #3861a1; }
QListWidget::item:hover { background: #101929; border-color: #263957; }
QTextEdit {
    color: #cbd5e1;
    background: #080c14;
    border: 1px solid #182336;
    border-radius: 10px;
    padding: 10px;
    selection-background-color: #2563eb;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 9pt;
}
QProgressBar {
    background: #0b111c;
    border: 1px solid #1a2638;
    border-radius: 4px;
    text-align: center;
    max-height: 6px;
    min-height: 6px;
}
QProgressBar::chunk { background: #3b82f6; border-radius: 3px; }
QSplitter::handle { background: #182232; width: 1px; margin: 4px 6px; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: #223047; border-radius: 4px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: #334869; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


def resource_path(relative: str) -> str:
    base = getattr(sys, "_MEIPASS", str(Path(__file__).resolve().parent.parent))
    return str(Path(base) / relative)


class DiagnosticWorker(QThread):
    item_done = Signal(object)
    progress = Signal(str)
    finished_all = Signal()

    def __init__(self, ids: list[str]):
        super().__init__()
        self.ids = list(ids)
        self.results = []

    def run(self):
        lookup = {item[0]: item[1] for item in CHECKS}
        for index, check_id in enumerate(self.ids, 1):
            self.progress.emit(f"Checking {index} of {len(self.ids)} · {lookup.get(check_id, check_id)}")
            result = run_check(check_id, self.progress.emit)
            self.results.append(result)
            self.item_done.emit(result)
        self.finished_all.emit()


class RepairWorker(QThread):
    progress = Signal(str)
    item_done = Signal(object)
    finished_all = Signal()

    def __init__(self, fix_ids: list[str]):
        super().__init__()
        self.fix_ids = list(fix_ids)
        self.results = []

    def run(self):
        titles = ", ".join(FIX_BY_ID[fid].title for fid in self.fix_ids if fid in FIX_BY_ID)
        self.progress.emit(f"Applying repair(s): {titles}…")
        batch_results = execute_fixes_batch(self.fix_ids)
        for result in batch_results:
            self.results.append(result)
            self.item_done.emit(result)
        self.finished_all.emit()


class CheckCard(QFrame):
    clicked = Signal(str)

    def __init__(self, check_id: str, title: str, description: str):
        super().__init__()
        self.setObjectName("SurfaceSoft")
        self.check_id = check_id
        self.default_description = description
        self.last_result = None
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(68)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(13, 10, 13, 9)
        layout.setSpacing(4)

        line = QHBoxLayout()
        self.checkbox = QCheckBox(title)
        self.checkbox.setChecked(check_id not in ("system_time", "traceroute"))
        self.checkbox.setStyleSheet("font-weight: 650;")
        line.addWidget(self.checkbox, 1)

        self.status = QLabel("READY")
        self.status.setObjectName("Tiny")
        self.status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        line.addWidget(self.status)
        layout.addLayout(line)

        self.description = QLabel(description)
        self.description.setObjectName("Tiny")
        self.description.setWordWrap(True)
        layout.addWidget(self.description)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.check_id)
        super().mousePressEvent(event)

    def set_result(self, result):
        self.last_result = result
        colors = {
            "PASS": "#34d399",
            "WARN": "#fbbf24",
            "FAIL": "#fb7185",
            "INFO": "#60a5fa",
            "SKIP": "#8798b0",
        }
        color = colors.get(result.status, "#8798b0")
        self.status.setText(result.status)
        self.status.setStyleSheet(f"color: {color}; font-size: 8pt; font-weight: 800;")
        if result.summary:
            self.description.setText(result.summary)

    def reset_status(self):
        self.last_result = None
        self.status.setText("QUEUED")
        self.status.setStyleSheet("color: #697b96; font-size: 8pt; font-weight: 750;")
        self.description.setText(self.default_description)


class MetricCard(QFrame):
    def __init__(self, label: str, key: str, color: str):
        super().__init__()
        self.setObjectName("Surface")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 13)
        layout.setSpacing(4)
        label_widget = QLabel(label.upper())
        label_widget.setObjectName("Tiny")
        layout.addWidget(label_widget)
        self.value = QLabel("—")
        self.value.setObjectName("MetricValue")
        self.value.setStyleSheet(f"color: {color};")
        layout.addWidget(self.value)
        self.key = key


class RepairCard(QFrame):
    def __init__(self, spec, callback):
        super().__init__()
        self.setObjectName("Surface")
        line = QHBoxLayout(self)
        line.setContentsMargins(16, 13, 16, 13)
        line.setSpacing(14)

        marker = QFrame()
        marker.setObjectName("AccentMark")
        if spec.impact == "HIGH":
            marker.setStyleSheet("background: #f43f5e; border-radius: 2px;")
        elif spec.impact == "MEDIUM":
            marker.setStyleSheet("background: #f59e0b; border-radius: 2px;")
        marker.setFixedSize(4, 44)
        line.addWidget(marker)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        title_line = QHBoxLayout()
        title_line.setSpacing(8)
        title = QLabel(spec.title)
        title.setObjectName("SectionTitle")
        title_line.addWidget(title)

        badge_text = "RESTART REQUIRED" if spec.reboot else ("ADMIN · UAC" if spec.requires_admin else "STANDARD")
        tag = QLabel(badge_text)
        tag.setObjectName("Pill")
        if spec.reboot:
            tag.setStyleSheet(
                "color: #fda4af; background: #29141d; border: 1px solid #572335; border-radius: 8px; padding: 3px 8px; font-size: 7.5pt; font-weight: 750;"
            )
        title_line.addWidget(tag, 0, Qt.AlignLeft)
        title_line.addStretch(1)
        text_col.addLayout(title_line)

        detail = QLabel(spec.description)
        detail.setObjectName("Muted")
        detail.setWordWrap(True)
        text_col.addWidget(detail)
        line.addLayout(text_col, 1)

        button = QPushButton("Run repair")
        button.setCursor(Qt.PointingHandCursor)
        if spec.impact == "HIGH":
            button.setObjectName("Danger")
        button.clicked.connect(lambda checked=False, fid=spec.id: callback(fid))
        button.setMinimumWidth(116)
        line.addWidget(button, 0, Qt.AlignVCenter)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setWindowIcon(QIcon(resource_path("assets/netscope.ico")))
        self.resize(1340, 860)
        self.setMinimumSize(1080, 720)
        self.cards: dict[str, CheckCard] = {}
        self.results = []
        self.worker: DiagnosticWorker | None = None
        self.repair_worker: RepairWorker | None = None
        self.last_report = None
        self.repair_history = []
        self.pending_rescan = False
        self.metric_cards: dict[str, MetricCard] = {}
        self.finding_data = []
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(216)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(15, 20, 15, 16)
        side.setSpacing(8)

        brand_line = QHBoxLayout()
        brand_line.setSpacing(11)
        brand_mark = QFrame()
        brand_mark.setObjectName("BrandMark")
        brand_mark.setFixedSize(42, 42)
        mark_layout = QVBoxLayout(brand_mark)
        mark_layout.setContentsMargins(5, 5, 5, 5)
        mark_icon = QLabel()
        mark_icon.setPixmap(QIcon(resource_path("assets/netscope.svg")).pixmap(28, 28))
        mark_icon.setAlignment(Qt.AlignCenter)
        mark_layout.addWidget(mark_icon)
        brand_line.addWidget(brand_mark)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        brand = QLabel("NetScope")
        brand.setObjectName("Brand")
        brand_text.addWidget(brand)
        brand_sub = QLabel(f"TOOLKIT v{APP_VERSION}")
        brand_sub.setObjectName("BrandSub")
        brand_text.addWidget(brand_sub)
        brand_line.addLayout(brand_text)
        side.addLayout(brand_line)
        side.addSpacing(26)

        nav_label = QLabel("WORKSPACE")
        nav_label.setObjectName("Tiny")
        nav_label.setStyleSheet("font-weight: 800; letter-spacing: 1.2px; padding-left: 8px;")
        side.addWidget(nav_label)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons = []
        nav_items = (
            ("Overview", "▦"),
            ("Repair center", "⌁"),
            ("Reports", "≡"),
        )
        for index, (label, icon) in enumerate(nav_items):
            button = QPushButton(f"  {icon}    {label}")
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(42)
            self.nav_group.addButton(button, index)
            side.addWidget(button)
            self.nav_buttons.append(button)
            button.clicked.connect(lambda checked=False, page=index: self.switch_page(page))
        self.nav_buttons[0].setChecked(True)

        side.addStretch(1)

        footer = QFrame()
        footer.setObjectName("SurfaceSoft")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(12, 11, 12, 11)
        footer_layout.setSpacing(3)
        coded = QLabel("Coded by EPINOR")
        coded.setObjectName("FooterBrand")
        footer_layout.addWidget(coded)
        sub_footer = QLabel("Local-first · Zero telemetry")
        sub_footer.setObjectName("Tiny")
        footer_layout.addWidget(sub_footer)
        side.addWidget(footer)
        root.addWidget(sidebar)

        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(26, 20, 26, 16)
        main_layout.setSpacing(14)

        topbar = QHBoxLayout()
        self.page_title = QLabel("Overview")
        self.page_title.setObjectName("PageTitle")
        topbar.addWidget(self.page_title)
        topbar.addStretch(1)

        priv_text = "ADMIN MODE" if is_admin() else ("STANDARD USER" if is_windows() else "NON-WINDOWS")
        self.privilege_pill = QLabel(priv_text)
        self.privilege_pill.setObjectName("Pill")
        topbar.addWidget(self.privilege_pill)
        topbar.addSpacing(8)

        self.scan_button = QPushButton("  Run full scan")
        self.scan_button.setObjectName("Primary")
        self.scan_button.setCursor(Qt.PointingHandCursor)
        self.scan_button.setIcon(QIcon(resource_path("assets/scan.svg")))
        self.scan_button.clicked.connect(self.run_all)
        topbar.addWidget(self.scan_button)
        main_layout.addLayout(topbar)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_overview_page())
        self.pages.addWidget(self._build_repairs_page())
        self.pages.addWidget(self._build_reports_page())
        main_layout.addWidget(self.pages, 1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        main_layout.addWidget(self.progress)

        status_line = QHBoxLayout()
        self.status_label = QLabel("Ready to scan")
        self.status_label.setObjectName("Muted")
        status_line.addWidget(self.status_label)
        status_line.addStretch(1)
        self.platform_label = QLabel("WINDOWS DIAGNOSTICS & REPAIR" if is_windows() else "DIAGNOSTICS ONLY (NON-WINDOWS)")
        self.platform_label.setObjectName("Tiny")
        status_line.addWidget(self.platform_label)
        main_layout.addLayout(status_line)
        root.addWidget(main, 1)

    def _build_overview_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(13)

        hero = QFrame()
        hero.setObjectName("Hero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(20, 15, 20, 15)
        hero_layout.setSpacing(15)
        self.hero_accent = QFrame()
        self.hero_accent.setObjectName("AccentMark")
        self.hero_accent.setFixedSize(4, 52)
        hero_layout.addWidget(self.hero_accent)

        hero_text = QVBoxLayout()
        hero_text.setSpacing(3)
        hero_heading = QLabel("NETWORK HEALTH STATUS")
        hero_heading.setObjectName("Tiny")
        hero_heading.setStyleSheet("font-weight: 800; letter-spacing: 0.8px;")
        hero_text.addWidget(hero_heading)
        self.hero_status = QLabel("Not tested yet")
        self.hero_status.setObjectName("HeroStatus")
        hero_text.addWidget(self.hero_status)
        self.hero_detail = QLabel("Run a diagnostic scan to evaluate local gateway, DNS, TCP, and HTTPS connectivity.")
        self.hero_detail.setObjectName("Muted")
        hero_text.addWidget(self.hero_detail)
        hero_layout.addLayout(hero_text, 1)

        self.hero_pill = QLabel("IDLE")
        self.hero_pill.setObjectName("Pill")
        hero_layout.addWidget(self.hero_pill, 0, Qt.AlignVCenter)
        layout.addWidget(hero)

        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        for key, label, color in (
            ("PASS", "Passed", "#34d399"),
            ("WARN", "Warnings", "#fbbf24"),
            ("FAIL", "Failed", "#fb7185"),
            ("TOTAL", "Checks run", "#e2e8f0"),
        ):
            card = MetricCard(label, key, color)
            self.metric_cards[key] = card
            metrics.addWidget(card)
        layout.addLayout(metrics)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)

        left_panel = QFrame()
        left_panel.setObjectName("Surface")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(15, 13, 15, 12)
        left_layout.setSpacing(10)
        head = QHBoxLayout()
        checks_title = QLabel("Diagnostic checks")
        checks_title.setObjectName("SectionTitle")
        head.addWidget(checks_title)
        head.addStretch(1)
        select_all = QPushButton("Toggle all")
        select_all.setCursor(Qt.PointingHandCursor)
        select_all.setMinimumHeight(28)
        select_all.setStyleSheet("padding: 4px 10px; font-size: 8.5pt;")
        select_all.clicked.connect(self.toggle_all_checks)
        head.addWidget(select_all)
        left_layout.addLayout(head)

        checks_scroll = QScrollArea()
        checks_scroll.setWidgetResizable(True)
        checks_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        checks_widget = QWidget()
        self.checks_grid = QGridLayout(checks_widget)
        self.checks_grid.setContentsMargins(0, 0, 4, 0)
        self.checks_grid.setSpacing(8)
        for index, (check_id, title, description) in enumerate(CHECKS):
            card = CheckCard(check_id, title, description)
            card.clicked.connect(self.on_check_card_clicked)
            self.cards[check_id] = card
            self.checks_grid.addWidget(card, index // 2, index % 2)
        self.checks_grid.setColumnStretch(0, 1)
        self.checks_grid.setColumnStretch(1, 1)
        checks_scroll.setWidget(checks_widget)
        left_layout.addWidget(checks_scroll, 1)

        run_row = QHBoxLayout()
        self.selected_scan_button = QPushButton("Run selected checks")
        self.selected_scan_button.setCursor(Qt.PointingHandCursor)
        self.selected_scan_button.clicked.connect(self.run_selected)
        run_row.addWidget(self.selected_scan_button)
        hint_lbl = QLabel("Click any check card to inspect its raw output")
        hint_lbl.setObjectName("Tiny")
        run_row.addStretch(1)
        run_row.addWidget(hint_lbl)
        left_layout.addLayout(run_row)

        right_panel = QFrame()
        right_panel.setObjectName("Surface")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 13, 15, 12)
        right_layout.setSpacing(10)
        right_head = QHBoxLayout()
        findings_title = QLabel("Heuristic findings")
        findings_title.setObjectName("SectionTitle")
        right_head.addWidget(findings_title)
        right_head.addStretch(1)
        self.findings_count = QLabel("0")
        self.findings_count.setObjectName("Pill")
        right_head.addWidget(self.findings_count)
        right_layout.addLayout(right_head)

        self.findings_list = QListWidget()
        self.findings_list.setSpacing(2)
        self.findings_list.itemClicked.connect(self.on_finding_selected)
        right_layout.addWidget(self.findings_list, 1)

        detail_label = QLabel("INSPECTOR / RAW DETAILS")
        detail_label.setObjectName("Tiny")
        detail_label.setStyleSheet("font-weight: 800; letter-spacing: 0.6px;")
        right_layout.addWidget(detail_label)
        self.finding_detail = QTextEdit()
        self.finding_detail.setReadOnly(True)
        self.finding_detail.setMaximumHeight(175)
        self.finding_detail.setPlaceholderText("Select a finding or click a check card to inspect detailed output.")
        right_layout.addWidget(self.finding_detail)

        split.addWidget(left_panel)
        split.addWidget(right_panel)
        split.setSizes([690, 420])
        layout.addWidget(split, 1)
        return page

    def _build_repairs_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(13)

        intro = QFrame()
        intro.setObjectName("Hero")
        intro_l = QVBoxLayout(intro)
        intro_l.setContentsMargins(20, 15, 20, 15)
        intro_l.setSpacing(6)
        intro_title = QLabel("Smart repair recommendations")
        intro_title.setObjectName("SectionTitle")
        intro_l.addWidget(intro_title)
        self.repair_summary = QLabel("Run diagnostics first so NetScope can match symptoms to safe, relevant repairs.")
        self.repair_summary.setObjectName("Muted")
        self.repair_summary.setWordWrap(True)
        intro_l.addWidget(self.repair_summary)

        action_line = QHBoxLayout()
        self.recommended_button = QPushButton("Fix recommended issues")
        self.recommended_button.setObjectName("Primary")
        self.recommended_button.setCursor(Qt.PointingHandCursor)
        self.recommended_button.clicked.connect(self.run_recommended_repairs)
        action_line.addWidget(self.recommended_button)

        self.proxy_settings_button = QPushButton("Open Windows proxy settings")
        self.proxy_settings_button.setCursor(Qt.PointingHandCursor)
        self.proxy_settings_button.clicked.connect(self.open_proxy_settings)
        action_line.addWidget(self.proxy_settings_button)
        action_line.addStretch(1)
        intro_l.addLayout(action_line)
        layout.addWidget(intro)

        advanced_label = QLabel("ALL REPAIR ACTIONS")
        advanced_label.setObjectName("Tiny")
        advanced_label.setStyleSheet("font-weight: 800; letter-spacing: 0.9px;")
        layout.addWidget(advanced_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        holder = QWidget()
        repair_layout = QVBoxLayout(holder)
        repair_layout.setContentsMargins(0, 0, 4, 0)
        repair_layout.setSpacing(9)
        self.repair_cards = {}
        for spec in FIXES:
            card = RepairCard(spec, self.run_single_repair)
            self.repair_cards[spec.id] = card
            repair_layout.addWidget(card)
        repair_layout.addStretch(1)
        scroll.setWidget(holder)
        layout.addWidget(scroll, 1)

        caution = QLabel(
            "Note: High-impact stack resets (Winsock / TCP-IP) are never triggered automatically and require a system restart."
        )
        caution.setObjectName("Tiny")
        caution.setWordWrap(True)
        layout.addWidget(caution)

        if not is_windows():
            self.recommended_button.setEnabled(False)
            self.proxy_settings_button.setEnabled(False)
            self.repair_summary.setText("Repair commands are supported on Windows only.")
        return page

    def _build_reports_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(13)

        header = QFrame()
        header.setObjectName("Surface")
        h = QHBoxLayout(header)
        h.setContentsMargins(16, 13, 16, 13)
        h.setSpacing(12)
        text_col = QVBoxLayout()
        title = QLabel("Diagnostic report & export")
        title.setObjectName("SectionTitle")
        text_col.addWidget(title)
        self.report_state = QLabel("A structured report will be generated here after your first scan.")
        self.report_state.setObjectName("Muted")
        text_col.addWidget(self.report_state)
        h.addLayout(text_col, 1)

        self.redact_checkbox = QCheckBox("Redact private details")
        self.redact_checkbox.setChecked(True)
        self.redact_checkbox.toggled.connect(self.refresh_report_preview)
        h.addWidget(self.redact_checkbox)

        self.export_txt_button = QPushButton("Export .txt")
        self.export_txt_button.setCursor(Qt.PointingHandCursor)
        self.export_txt_button.clicked.connect(self.export_text)
        self.export_json_button = QPushButton("Export .json")
        self.export_json_button.setCursor(Qt.PointingHandCursor)
        self.export_json_button.clicked.connect(self.export_json_file)
        self.copy_button = QPushButton("Copy report")
        self.copy_button.setObjectName("Primary")
        self.copy_button.setCursor(Qt.PointingHandCursor)
        self.copy_button.clicked.connect(self.copy_findings)
        for button in (self.export_txt_button, self.export_json_button, self.copy_button):
            button.setEnabled(False)
            h.addWidget(button)
        layout.addWidget(header)

        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        self.report_view.setPlaceholderText("Run a diagnostic scan to populate this report.")
        layout.addWidget(self.report_view, 1)

        privacy = QLabel(
            "When 'Redact private details' is checked, local IPv4 addresses, MAC addresses, Wi-Fi SSIDs, hostnames, and usernames are masked."
        )
        privacy.setObjectName("Tiny")
        privacy.setWordWrap(True)
        layout.addWidget(privacy)
        return page

    def switch_page(self, index: int):
        self.pages.setCurrentIndex(index)
        self.page_title.setText(("Overview", "Repair center", "Reports")[index])
        if index < len(self.nav_buttons):
            self.nav_buttons[index].setChecked(True)

    def toggle_all_checks(self):
        all_checked = all(card.checkbox.isChecked() for card in self.cards.values())
        for card in self.cards.values():
            card.checkbox.setChecked(not all_checked)

    def on_check_card_clicked(self, check_id: str):
        card = self.cards.get(check_id)
        if not card or not card.last_result:
            return
        r = card.last_result
        self.finding_detail.setPlainText(
            f"[{r.status}] {r.title} ({r.duration_ms} ms)\n"
            f"Summary: {r.summary}\n\n"
            f"{r.details}\n\n"
            f"Suggested next step: {r.remediation}".strip()
        )

    def run_selected(self):
        ids = [check_id for check_id, card in self.cards.items() if card.checkbox.isChecked()]
        if not ids:
            QMessageBox.information(self, "No checks selected", "Select at least one diagnostic check to run.")
            return
        self.start_scan(ids)

    def run_all(self):
        self.start_scan([item[0] for item in CHECKS])

    def start_scan(self, ids: list[str]):
        if self.worker and self.worker.isRunning():
            return
        if self.repair_worker and self.repair_worker.isRunning():
            return
        self.results = []
        self.last_report = None
        for cid, card in self.cards.items():
            if cid in ids:
                card.reset_status()
        self.findings_list.clear()
        self.finding_detail.clear()
        self.findings_count.setText("0")
        self.hero_status.setText("Scanning network…")
        self.hero_detail.setText("Testing local adapter, gateway, DNS resolution, HTTPS, and routing.")
        self.hero_pill.setText("SCANNING")
        self.hero_accent.setStyleSheet("background: #3b82f6; border-radius: 2px;")
        self.progress.setRange(0, len(ids))
        self.progress.setValue(0)
        self._set_busy(True)
        self.switch_page(0)
        self.status_label.setText("Starting diagnostics…")
        self.worker = DiagnosticWorker(ids)
        self.worker.item_done.connect(self.on_result)
        self.worker.progress.connect(self.status_label.setText)
        self.worker.finished_all.connect(self.on_scan_finished)
        self.worker.start()

    def _set_busy(self, busy: bool):
        self.scan_button.setEnabled(not busy)
        self.selected_scan_button.setEnabled(not busy)
        self.recommended_button.setEnabled(not busy and is_windows())
        for card in self.repair_cards.values():
            for button in card.findChildren(QPushButton):
                button.setEnabled(not busy and is_windows())

    def on_result(self, result):
        self.results.append(result)
        if result.id in self.cards:
            self.cards[result.id].set_result(result)
        self.progress.setValue(len(self.results))
        self.metric_cards["TOTAL"].value.setText(str(len(self.results)))
        for status in ("PASS", "WARN", "FAIL"):
            count = sum(r.status == status for r in self.results)
            self.metric_cards[status].value.setText(str(count))
        self.on_check_card_clicked(result.id)

    def on_scan_finished(self):
        self.last_report = build_report(self.results)
        self._set_busy(False)
        self.render_findings()
        failures = sum(r.status == "FAIL" for r in self.results)
        warnings = sum(r.status == "WARN" for r in self.results)
        findings = analyse_results(self.results)
        has_critical = any(item.get("level") == "critical" for item in findings)
        has_warning = any(item.get("level") == "warning" for item in findings)

        if has_critical:
            self.hero_status.setText("Connectivity issues detected")
            self.hero_detail.setText(
                f"{failures} failed check(s) · {warnings} warning(s). Review heuristic findings and recommended repairs."
            )
            self.hero_pill.setText("ACTION NEEDED")
            self.hero_accent.setStyleSheet("background: #f43f5e; border-radius: 2px;")
        elif has_warning or warnings:
            self.hero_status.setText("Completed with warnings")
            self.hero_detail.setText(
                f"{failures} failed check(s) · {warnings} warning(s). Some probes may be filtered by router or ISP policy."
            )
            self.hero_pill.setText("REVIEW")
            self.hero_accent.setStyleSheet("background: #f59e0b; border-radius: 2px;")
        else:
            self.hero_status.setText("Network appears healthy")
            self.hero_detail.setText("All selected diagnostic checks completed with no clear connectivity fault.")
            self.hero_pill.setText("HEALTHY")
            self.hero_accent.setStyleSheet("background: #10b981; border-radius: 2px;")

        self.report_state.setText(
            f"Last scan: {len(self.results)} checks · {datetime.datetime.now().astimezone():%Y-%m-%d %H:%M}"
        )
        self.refresh_report_preview()
        for button in (self.export_txt_button, self.export_json_button, self.copy_button):
            button.setEnabled(True)
        self.repair_summary.setText(self.repair_recommendation_summary())
        self.status_label.setText(f"Scan complete · {len(self.results)} checks executed")

    def render_findings(self):
        self.findings_list.clear()
        self.finding_data = analyse_results(self.results)
        if not self.finding_data:
            self.finding_data = [
                {
                    "level": "info",
                    "title": "No analysis available",
                    "detail": "Run a scan to analyze network health.",
                    "fixes": [],
                }
            ]
        colors = {
            "critical": "#fb7185",
            "warning": "#fbbf24",
            "info": "#60a5fa",
            "success": "#34d399",
        }
        for data in self.finding_data:
            item = QListWidgetItem(f"●   {data['title']}")
            item.setForeground(QColor(colors.get(data["level"], "#dce6f5")))
            item.setData(Qt.UserRole, data)
            self.findings_list.addItem(item)
        self.findings_count.setText(str(len(self.finding_data)))
        if self.findings_list.count():
            self.findings_list.setCurrentRow(0)
            self.on_finding_selected(self.findings_list.item(0))

    def on_finding_selected(self, item):
        data = item.data(Qt.UserRole)
        fixes = data.get("fixes", [])
        fix_lines = [f"• {FIX_BY_ID[f].title}: {FIX_BY_ID[f].description}" for f in fixes if f in FIX_BY_ID]
        content = f"[{data.get('level', 'info').upper()}] {data.get('title', '')}\n\n{data.get('detail', '')}"
        if fix_lines:
            content += "\n\nRecommended repair(s):\n" + "\n".join(fix_lines)
        self.finding_detail.setPlainText(content)

    def repair_recommendation_summary(self):
        if not self.results:
            return "Run diagnostics first so NetScope can match symptoms to relevant repairs."
        fixes = recommended_fixes(self.results)
        if fixes:
            names = ", ".join(FIX_BY_ID[f].title for f in fixes)
            return f"Recommended based on scan results: {names}. Click 'Fix recommended issues' to review and apply."
        return "No automatic low-risk repair is needed right now. Individual repair tools remain available below."

    def run_recommended_repairs(self):
        if not self.results:
            QMessageBox.information(self, "Scan first", "Run a diagnostic scan before running recommended repairs.")
            return
        fix_ids = recommended_fixes(self.results)
        if not fix_ids:
            QMessageBox.information(
                self,
                "No automatic fix needed",
                "The scan did not indicate a clear match for a low-risk automatic repair.",
            )
            return
        labels = [f"• {FIX_BY_ID[fid].title}\n  {FIX_BY_ID[fid].description}" for fid in fix_ids]
        question = (
            "NetScope will execute the following repair action(s):\n\n"
            + "\n\n".join(labels)
            + "\n\nWindows may request administrator approval (UAC) once. Continue?"
        )
        answer = QMessageBox.question(
            self,
            "Confirm recommended repairs",
            question,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.start_repairs(fix_ids, rescan_after=True)

    def run_single_repair(self, fix_id: str):
        if not is_windows():
            QMessageBox.information(self, "Windows only", "Repair commands are supported on Windows only.")
            return
        spec = FIX_BY_ID[fix_id]
        impact_line = (
            "A Windows restart will be required to complete this reset."
            if spec.reboot
            else ("This may briefly interrupt active network connections." if fix_id == "renew_dhcp" else "")
        )
        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Warning if spec.impact == "HIGH" else QMessageBox.Question)
        confirm.setWindowTitle("Confirm repair")
        confirm.setText(spec.title)
        confirm.setInformativeText(
            spec.description + ("\n\n" + impact_line if impact_line else "") + "\n\nRun this repair now?"
        )
        confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        confirm.setDefaultButton(QMessageBox.Cancel)
        if confirm.exec() == QMessageBox.Yes:
            self.start_repairs([fix_id], rescan_after=not spec.reboot)

    def start_repairs(self, fix_ids: list[str], rescan_after: bool = False):
        if self.repair_worker and self.repair_worker.isRunning():
            return
        if not is_windows():
            return
        self.pending_rescan = rescan_after
        self.repair_history = []
        self.progress.setRange(0, len(fix_ids))
        self.progress.setValue(0)
        self._set_busy(True)
        self.switch_page(1)
        self.status_label.setText("Starting repair…")
        self.repair_worker = RepairWorker(fix_ids)
        self.repair_worker.progress.connect(self.status_label.setText)
        self.repair_worker.item_done.connect(self.on_repair_result)
        self.repair_worker.finished_all.connect(self.on_repairs_finished)
        self.repair_worker.start()

    def on_repair_result(self, result: dict):
        self.repair_history.append(result)
        self.progress.setValue(len(self.repair_history))
        status = "SUCCESS" if result.get("ok") else "FAILED"
        spec = FIX_BY_ID.get(result.get("fix_id", ""))
        title = spec.title if spec else "Repair"
        self.finding_detail.setPlainText(
            f"{title}\nStatus: {status}\n\n{result.get('summary', '')}\n\n{result.get('details', '')}"
        )

    def on_repairs_finished(self):
        self._set_busy(False)
        failures = [r for r in self.repair_history if not r.get("ok")]
        reboot = any(r.get("reboot_required") for r in self.repair_history)
        self.status_label.setText("Repair complete" if not failures else "Repair finished with errors")
        summary = "\n".join(
            ("SUCCESS" if r.get("ok") else "FAILED")
            + " — "
            + FIX_BY_ID[r["fix_id"]].title
            + ": "
            + r.get("summary", "")
            for r in self.repair_history
            if r.get("fix_id") in FIX_BY_ID
        )
        self.repair_summary.setText(summary or "Repair process finished.")
        self.refresh_report_preview()
        if reboot:
            QMessageBox.information(
                self,
                "Restart required",
                "The network stack reset completed. Restart Windows before evaluating connectivity.",
            )
        elif self.pending_rescan and not failures:
            QMessageBox.information(
                self,
                "Repairs completed",
                "The selected repairs completed. NetScope will now re-run diagnostics to verify connectivity.",
            )
            QTimer.singleShot(350, self.run_all)
        elif failures:
            details = "\n\n".join(f"{r.get('summary', '')}\n{r.get('details', '')}" for r in failures)
            QMessageBox.warning(self, "Repair issue", details[:3000])

    def open_proxy_settings(self):
        if not is_windows():
            return
        try:
            os.startfile("ms-settings:network-proxy")
        except Exception as exc:
            QMessageBox.warning(self, "Could not open settings", str(exc))

    def _report_text_with_analysis(self, redact: bool | None = None) -> str:
        if redact is None:
            redact = self.redact_checkbox.isChecked()
        base = report_as_text(self.last_report, redact=False) if self.last_report else "NETSCOPE REPORT\nNo scan available."
        lines = [base, "", "DIAGNOSTIC ANALYSIS", "=" * 42]
        for finding in analyse_results(self.results):
            lines.extend([f"[{finding['level'].upper()}] {finding['title']}", finding["detail"]])
            fixes = [FIX_BY_ID[x].title for x in finding.get("fixes", []) if x in FIX_BY_ID]
            if fixes:
                lines.append("Potential repairs: " + ", ".join(fixes))
            lines.append("")
        if self.repair_history:
            lines.extend(["REPAIR HISTORY", "=" * 42])
            for result in self.repair_history:
                spec = FIX_BY_ID.get(result.get("fix_id"))
                title = spec.title if spec else result.get("fix_id", "Repair")
                status = "SUCCESS" if result.get("ok") else "FAILED"
                lines.append(f"[{status}] {title}: {result.get('summary', '')}")
                if result.get("details"):
                    lines.append(result["details"])
                lines.append("")
        full_text = "\n".join(lines)
        return redact_sensitive_text(full_text) if redact else full_text

    def refresh_report_preview(self):
        if self.last_report:
            self.report_view.setPlainText(self._report_text_with_analysis())

    def export_text(self):
        if not self.last_report:
            return
        default = f"NetScope-report-{datetime.datetime.now():%Y%m%d-%H%M%S}.txt"
        path, _ = QFileDialog.getSaveFileName(self, "Export report", default, "Text report (*.txt)")
        if path:
            try:
                Path(path).write_text(self._report_text_with_analysis(), encoding="utf-8")
                QMessageBox.information(self, "Exported", "Text report saved successfully.")
            except Exception as exc:
                QMessageBox.critical(self, "Export failed", str(exc))

    def export_json_file(self):
        if not self.last_report:
            return
        default = f"NetScope-report-{datetime.datetime.now():%Y%m%d-%H%M%S}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Export JSON report", default, "JSON report (*.json)")
        if path:
            try:
                payload = self.last_report.__dict__.copy()
                payload["findings_analysis"] = analyse_results(self.results)
                payload["repair_history"] = self.repair_history
                raw_json = json.dumps(payload, indent=2, ensure_ascii=False)
                if self.redact_checkbox.isChecked():
                    raw_json = redact_sensitive_text(raw_json)
                Path(path).write_text(raw_json, encoding="utf-8")
                QMessageBox.information(self, "Exported", "JSON report saved successfully.")
            except Exception as exc:
                QMessageBox.critical(self, "Export failed", str(exc))

    def copy_findings(self):
        if self.last_report:
            QApplication.clipboard().setText(self._report_text_with_analysis())
            self.status_label.setText("Report copied to clipboard")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()