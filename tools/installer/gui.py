"""Simple PySide6 GUI PoC for the installer.

Install requirement for GUI PoC: `pip install PySide6`
"""
import sys
import logging
import datetime
import os
import re
import json
import shutil

# Attempt to import PySide6 widgets and core. In headless/CI environments this may fail.
try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QPushButton, QMessageBox, QCheckBox, QRadioButton, QTextEdit, QProgressBar, QFileDialog,
        QTabWidget, QListWidget, QListWidgetItem, QComboBox
    )
    from PySide6.QtCore import QObject, Signal, Slot, QThread
    from PySide6.QtGui import QPalette, QColor
except Exception as e:
    PySide6 = None
    _gui_import_error = e
else:
    _gui_import_error = None

from .core import install_all, uninstall_all, start_component_service, stop_component_service
from .os_utils import is_admin

log = logging.getLogger(__name__)


# Built-in i18n strings (defaults)
_STRINGS = {
    "en": {
        "title": "Panel Installer (PoC)",
        "install_uninstall": "Install/Uninstall",
        "services": "Services",
        "logs": "Logs",
        "settings": "Settings",
        "domain": "Domain:",
        "postgres": "Postgres",
        "redis": "Redis",
        "nginx": "Nginx",
        "python": "Python Env",
        "install": "Install",
        "uninstall": "Uninstall",
        "dry_run": "Dry-run (show commands only)",
        "preserve": "Preserve data (during uninstall)",
        "dark_mode": "Dark Mode",
        "run": "Run",
        "cancel": "Cancel",
        "preflight": "Preflight Checks",
        "export_text": "Export Text Log…",
        "export_json": "Export JSON Log…",
        "db_user": "DB User:",
        "db_pass": "DB Password:",
        "redis_port": "Redis Port:",
        "nginx_port": "Nginx Port:",
        "tls_cert": "TLS Cert Path:",
        "tls_key": "TLS Key Path:",
        "validate_settings": "Validate Settings",
        "language": "Language:",
        "retry": "Retries:",
        "backoff_ms": "Backoff ms:",
        "cli_equiv": "Show CLI Command",
        "services_start": "Start",
        "services_stop": "Stop",
        "services_restart": "Restart",
        "services_status": "Status",
    }
}


def _load_external_translations():
    """Load external translation JSON files from `tools/installer/i18n/*.json`.
    Each file should be named with the locale code, e.g., `es.json`, and contain a flat key-value map.
    External entries override built-in strings for the same locale.
    """
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        i18n_dir = os.path.join(base_dir, "i18n")
        if not os.path.isdir(i18n_dir):
            return
        for name in os.listdir(i18n_dir):
            if not name.endswith(".json"):
                continue
            locale = os.path.splitext(name)[0]
            path = os.path.join(i18n_dir, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    continue
                # merge/override
                existing = _STRINGS.get(locale, {})
                merged = {**existing, **data}
                _STRINGS[locale] = merged
            except Exception:
                # ignore bad files
                continue
    except Exception:
        pass


class Worker(QObject):
    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(str, str, dict)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._cancelled = False
        self.max_retries = kwargs.pop("_max_retries", 0)
        self.backoff_ms = kwargs.pop("_backoff_ms", 0)

    def cancel(self):
        self._cancelled = True

    def _progress_cb(self, step, component, meta):
        self.progress.emit(step, component or "", meta or {})

    @Slot()
    def run(self):
        try:
            if self._cancelled:
                self.finished.emit({"status": "cancelled"})
                return
            self.kwargs["progress_cb"] = self._progress_cb
            attempt = 0
            while attempt <= self.max_retries:
                try:
                    res = self.func(*self.args, **self.kwargs)
                    self.finished.emit(res)
                    return
                except Exception as e:
                    self.progress.emit("retry", "", {"attempt": attempt, "error": str(e)})
                    if attempt >= self.max_retries:
                        raise
                    import time
                    time.sleep(max(self.backoff_ms, 0) / 1000.0)
                    attempt += 1
        except Exception as e:
            self.error.emit(str(e))


class InstallerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Load external translations before building UI
        _load_external_translations()
        self.lang = "en"
        self.str = _STRINGS[self.lang]
        self.setWindowTitle(self.str["title"])
        self._log_file_path = None
        self._json_log_file_path = None
        self._progress_total = 100
        self._progress_per_component = {}
        self._build_ui()
        self._apply_platform_rules()

    def _tr(self, key):
        return self.str.get(key, key)

    def _build_ui(self):
        self.tabs = QTabWidget()

        # Install/Uninstall tab
        self.main_tab = QWidget(); main_layout = QVBoxLayout()
        self.lang_h = QHBoxLayout()
        self.lang_label = QLabel(self._tr("language"))
        self.lang_select = QComboBox(); self.lang_select.addItems(list(_STRINGS.keys())); self.lang_select.currentTextChanged.connect(self._on_lang_change)
        self.lang_h.addWidget(self.lang_label)
        self.lang_h.addWidget(self.lang_select)
        main_layout.addLayout(self.lang_h)

        self.domain_h = QHBoxLayout()
        self.domain_label = QLabel(self._tr("domain"))
        self.domain_input = QLineEdit("localhost")
        self.domain_h.addWidget(self.domain_label)
        self.domain_h.addWidget(self.domain_input)
        main_layout.addLayout(self.domain_h)

        self.chk_postgres = QCheckBox(self._tr("postgres")); self.chk_postgres.setChecked(True)
        self.chk_redis = QCheckBox(self._tr("redis")); self.chk_redis.setChecked(True)
        self.chk_nginx = QCheckBox(self._tr("nginx")); self.chk_nginx.setChecked(True)
        self.chk_python = QCheckBox(self._tr("python")); self.chk_python.setChecked(True)
        self.chk_nginx.stateChanged.connect(self._on_component_toggle)
        self.chk_python.stateChanged.connect(self._on_component_toggle)
        self.chk_postgres.stateChanged.connect(self._on_component_toggle)
        main_layout.addWidget(self.chk_postgres)
        main_layout.addWidget(self.chk_redis)
        main_layout.addWidget(self.chk_nginx)
        main_layout.addWidget(self.chk_python)

        self.install_radio = QRadioButton(self._tr("install")); self.install_radio.setChecked(True)
        self.uninstall_radio = QRadioButton(self._tr("uninstall"))
        main_layout.addWidget(self.install_radio)
        main_layout.addWidget(self.uninstall_radio)

        self.opt_h = QHBoxLayout()
        self.dry_run_check = QCheckBox(self._tr("dry_run")); self.opt_h.addWidget(self.dry_run_check)
        self.preserve_data_check = QCheckBox(self._tr("preserve")); self.preserve_data_check.setChecked(True); self.opt_h.addWidget(self.preserve_data_check)
        self.dark_mode_check = QCheckBox(self._tr("dark_mode")); self.dark_mode_check.stateChanged.connect(self._toggle_theme); self.opt_h.addWidget(self.dark_mode_check)
        main_layout.addLayout(self.opt_h)

        self.retry_h = QHBoxLayout()
        self.retry_label = QLabel(self._tr("retry"))
        self.retry_count = QLineEdit("0"); self.retry_h.addWidget(self.retry_label); self.retry_h.addWidget(self.retry_count)
        self.backoff_label = QLabel(self._tr("backoff_ms"))
        self.backoff_ms = QLineEdit("0"); self.retry_h.addWidget(self.backoff_label); self.retry_h.addWidget(self.backoff_ms)
        main_layout.addLayout(self.retry_h)

        self.btns_h = QHBoxLayout()
        self.btn_action = QPushButton(self._tr("run")); self.btn_action.clicked.connect(self._on_run); self.btns_h.addWidget(self.btn_action)
        self.btn_cancel = QPushButton(self._tr("cancel")); self.btn_cancel.setEnabled(False); self.btn_cancel.clicked.connect(self._on_cancel); self.btns_h.addWidget(self.btn_cancel)
        self.btn_preflight = QPushButton(self._tr("preflight")); self.btn_preflight.clicked.connect(self._run_preflight); self.btns_h.addWidget(self.btn_preflight)
        self.btn_cli = QPushButton(self._tr("cli_equiv")); self.btn_cli.clicked.connect(self._show_cli_command); self.btns_h.addWidget(self.btn_cli)
        main_layout.addLayout(self.btns_h)

        self.progress = QProgressBar(); self.progress.setMinimum(0); self.progress.setMaximum(100); self.progress.setValue(0)
        main_layout.addWidget(self.progress)

        self.main_tab.setLayout(main_layout)
        self.tabs.addTab(self.main_tab, self._tr("install_uninstall"))

        # Services tab
        self.services_tab = QWidget(); services_layout = QVBoxLayout()
        self.services_list = QListWidget()
        for comp in ["postgres", "redis", "nginx", "python"]:
            self.services_list.addItem(QListWidgetItem(comp))
        self.svc_btns = QHBoxLayout()
        self.btn_service_start = QPushButton(self._tr("services_start")); self.btn_service_start.clicked.connect(lambda: self._service_action("start")); self.svc_btns.addWidget(self.btn_service_start)
        self.btn_service_stop = QPushButton(self._tr("services_stop")); self.btn_service_stop.clicked.connect(lambda: self._service_action("stop")); self.svc_btns.addWidget(self.btn_service_stop)
        self.btn_service_restart = QPushButton(self._tr("services_restart")); self.btn_service_restart.clicked.connect(lambda: self._service_action("restart")); self.svc_btns.addWidget(self.btn_service_restart)
        self.btn_service_status = QPushButton(self._tr("services_status")); self.btn_service_status.clicked.connect(lambda: self._service_action("status")); self.svc_btns.addWidget(self.btn_service_status)
        services_layout.addWidget(self.services_list)
        services_layout.addLayout(self.svc_btns)
        self.services_tab.setLayout(services_layout)
        self.tabs.addTab(self.services_tab, self._tr("services"))

        # Logs tab
        self.logs_tab = QWidget(); logs_layout = QVBoxLayout()
        self.output = QTextEdit(); self.output.setReadOnly(True)
        logs_layout.addWidget(self.output)
        self.export_h = QHBoxLayout()
        self.btn_save_log = QPushButton(self._tr("export_text")); self.btn_save_log.clicked.connect(self._on_export_log); self.export_h.addWidget(self.btn_save_log)
        self.btn_save_json_log = QPushButton(self._tr("export_json")); self.btn_save_json_log.clicked.connect(self._on_export_json_log); self.export_h.addWidget(self.btn_save_json_log)
        logs_layout.addLayout(self.export_h)
        self.logs_tab.setLayout(logs_layout)
        self.tabs.addTab(self.logs_tab, self._tr("logs"))

        # Settings tab
        self.settings_tab = QWidget(); settings_layout = QVBoxLayout()
        self.db_h = QHBoxLayout(); self.db_label = QLabel(self._tr("db_user")); self.db_user = QLineEdit("panel"); self.db_h.addWidget(self.db_label); self.db_h.addWidget(self.db_user); settings_layout.addLayout(self.db_h)
        self.dp_h = QHBoxLayout(); self.dp_label = QLabel(self._tr("db_pass")); self.db_pass = QLineEdit(""); self.db_pass.setEchoMode(QLineEdit.Password); self.dp_h.addWidget(self.dp_label); self.dp_h.addWidget(self.db_pass); settings_layout.addLayout(self.dp_h)
        self.rp_h = QHBoxLayout(); self.rp_label = QLabel(self._tr("redis_port")); self.redis_port = QLineEdit("6379"); self.rp_h.addWidget(self.rp_label); self.rp_h.addWidget(self.redis_port); settings_layout.addLayout(self.rp_h)
        self.np_h = QHBoxLayout(); self.np_label = QLabel(self._tr("nginx_port")); self.nginx_port = QLineEdit("80"); self.np_h.addWidget(self.np_label); self.np_h.addWidget(self.nginx_port); settings_layout.addLayout(self.np_h)
        self.tls_h = QHBoxLayout(); self.tls_cert_label = QLabel(self._tr("tls_cert")); self.tls_cert = QLineEdit(""); self.tls_h.addWidget(self.tls_cert_label); self.tls_h.addWidget(self.tls_cert); settings_layout.addLayout(self.tls_h)
        self.tlsk_h = QHBoxLayout(); self.tls_key_label = QLabel(self._tr("tls_key")); self.tls_key = QLineEdit(""); self.tlsk_h.addWidget(self.tls_key_label); self.tlsk_h.addWidget(self.tls_key); settings_layout.addLayout(self.tlsk_h)
        self.btn_validate_settings = QPushButton(self._tr("validate_settings")); self.btn_validate_settings.clicked.connect(self._validate_settings); settings_layout.addWidget(self.btn_validate_settings)
        self.settings_tab.setLayout(settings_layout)
        self.tabs.addTab(self.settings_tab, self._tr("settings"))

        self.setCentralWidget(self.tabs)
        self._last_error_text = ""

    def _on_lang_change(self, lang):
        self.lang = lang
        self.str = _STRINGS.get(self.lang, _STRINGS["en"])
        # Update window title and tab labels
        self.setWindowTitle(self._tr("title"))
        idx = self.tabs.indexOf(self.main_tab); self.tabs.setTabText(idx, self._tr("install_uninstall"))
        idx = self.tabs.indexOf(self.services_tab); self.tabs.setTabText(idx, self._tr("services"))
        idx = self.tabs.indexOf(self.logs_tab); self.tabs.setTabText(idx, self._tr("logs"))
        idx = self.tabs.indexOf(self.settings_tab); self.tabs.setTabText(idx, self._tr("settings"))
        # Relabel all controls
        self.lang_label.setText(self._tr("language"))
        self.domain_label.setText(self._tr("domain"))
        self.chk_postgres.setText(self._tr("postgres"))
        self.chk_redis.setText(self._tr("redis"))
        self.chk_nginx.setText(self._tr("nginx"))
        self.chk_python.setText(self._tr("python"))
        self.install_radio.setText(self._tr("install"))
        self.uninstall_radio.setText(self._tr("uninstall"))
        self.dry_run_check.setText(self._tr("dry_run"))
        self.preserve_data_check.setText(self._tr("preserve"))
        self.dark_mode_check.setText(self._tr("dark_mode"))
        self.retry_label.setText(self._tr("retry"))
        self.backoff_label.setText(self._tr("backoff_ms"))
        self.btn_action.setText(self._tr("run"))
        self.btn_cancel.setText(self._tr("cancel"))
        self.btn_preflight.setText(self._tr("preflight"))
        self.btn_cli.setText(self._tr("cli_equiv"))
        self.btn_service_start.setText(self._tr("services_start"))
        self.btn_service_stop.setText(self._tr("services_stop"))
        self.btn_service_restart.setText(self._tr("services_restart"))
        self.btn_service_status.setText(self._tr("services_status"))
        self.btn_save_log.setText(self._tr("export_text"))
        self.btn_save_json_log.setText(self._tr("export_json"))
        self.db_label.setText(self._tr("db_user"))
        self.dp_label.setText(self._tr("db_pass"))
        self.rp_label.setText(self._tr("redis_port"))
        self.np_label.setText(self._tr("nginx_port"))
        self.tls_cert_label.setText(self._tr("tls_cert"))
        self.tls_key_label.setText(self._tr("tls_key"))
        self.btn_validate_settings.setText(self._tr("validate_settings"))

    def _apply_platform_rules(self):
        pass

    def _toggle_theme(self):
        dark = self.dark_mode_check.isChecked()
        palette = QPalette()
        if dark:
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
            palette.setColor(QPalette.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.Text, QColor(255, 255, 255))
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        QApplication.instance().setPalette(palette)

    def _append_output(self, text, json_obj=None):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {text}"
        self.output.append(line)
        if not hasattr(self, '_log_file_path') or not hasattr(self, '_json_log_file_path') or not self._log_file_path or not self._json_log_file_path:
            try:
                logs_dir = os.path.join(os.path.expanduser("~"), ".panel_installer")
                os.makedirs(logs_dir, exist_ok=True)
                today = datetime.datetime.now().strftime('%Y%m%d')
                self._log_file_path = os.path.join(logs_dir, f"installer-{today}.log")
                self._json_log_file_path = os.path.join(logs_dir, f"installer-{today}.jsonl")
            except Exception:
                self._log_file_path = None
                self._json_log_file_path = None
        if self._log_file_path:
            try:
                with open(self._log_file_path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception:
                pass
        if self._json_log_file_path:
            try:
                record = {"ts": datetime.datetime.now().isoformat(), "message": text}
                if json_obj is not None:
                    record["data"] = json_obj
                with open(self._json_log_file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")
            except Exception:
                pass

    def _selected_components(self):
        comps = []
        if self.chk_postgres.isChecked(): comps.append("postgres")
        if self.chk_redis.isChecked(): comps.append("redis")
        if self.chk_nginx.isChecked(): comps.append("nginx")
        if self.chk_python.isChecked(): comps.append("python")
        return comps

    def _resolve_dependencies(self, components, mode):
        resolved = set(components)
        notes = []
        if mode == "install":
            if "nginx" in resolved and "python" not in resolved:
                resolved.add("python"); self.chk_python.setChecked(True)
                notes.append("Auto-selected Python because Nginx requires a backend.")
            if "postgres" in resolved and "redis" not in resolved:
                notes.append("Recommendation: Add Redis for caching/queue when using Postgres.")
        else:
            order = ["nginx", "python", "redis", "postgres"]
            sorted_list = [c for c in order if c in resolved]
            return sorted_list, notes
        return list(resolved), notes

    def _on_component_toggle(self):
        if self.install_radio.isChecked():
            comps = self._selected_components()
            resolved, notes = self._resolve_dependencies(comps, "install")
            for n in notes: self._append_output(n)

    def _validate_domain(self, domain: str) -> bool:
        if domain.lower() == "localhost": return True
        pattern = r"^(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
        return re.match(pattern, domain) is not None

    def _run_preflight(self):
        checks = []
        try:
            total, used, free = shutil.disk_usage(os.path.expanduser("~"))
            checks.append({"check": "disk_space", "free_gb": round(free / (1024**3), 2)})
        except Exception as e:
            checks.append({"check": "disk_space", "error": str(e)})
        checks.append({"check": "python_version", "version": sys.version})
        checks.append({"check": "pyside6", "available": PySide6 is not None})
        offline = False
        try:
            import urllib.request
            urllib.request.urlopen("https://www.microsoft.com", timeout=2)
        except Exception:
            offline = True
        checks.append({"check": "internet", "offline": offline})
        ports = [80, 443, 5432, 6379]
        port_results = {}
        import socket
        for p in ports:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(0.2)
            try:
                res = s.connect_ex(("127.0.0.1", p)); port_results[str(p)] = (res != 0)
            except Exception:
                port_results[str(p)] = None
            finally:
                s.close()
        checks.append({"check": "ports_free", "results": port_results})
        self._append_output("Preflight completed", checks)
        QMessageBox.information(self, "Preflight", json.dumps(checks, indent=2))

    def _validate_settings(self):
        errors = []
        if self.db_user.text().strip() == "": errors.append("DB user cannot be empty")
        pw = self.db_pass.text();
        if len(pw) < 8: errors.append("DB password should be at least 8 characters")
        try:
            rp = int(self.redis_port.text()); np = int(self.nginx_port.text())
            if rp <= 0 or rp > 65535: errors.append("Invalid Redis port")
            if np <= 0 or np > 65535: errors.append("Invalid Nginx port")
        except Exception:
            errors.append("Ports must be numeric")
        for p in [self.tls_cert.text(), self.tls_key.text()]:
            if p and not os.path.exists(p): errors.append(f"Path not found: {p}")
        if errors:
            msg = "\n".join(errors)
            self._append_output("Settings validation failed", {"errors": errors})
            QMessageBox.warning(self, "Settings", msg)
        else:
            self._append_output("Settings validated", {"db_user": self.db_user.text(), "redis_port": self.redis_port.text(), "nginx_port": self.nginx_port.text(), "tls_cert": bool(self.tls_cert.text()), "tls_key": bool(self.tls_key.text())})
            QMessageBox.information(self, "Settings", "Settings look good")

    def _show_cli_command(self):
        # Align with tools/installer/cli.py
        comps = self._selected_components()
        mode = "install" if self.install_radio.isChecked() else "uninstall"
        dry = self.dry_run_check.isChecked()
        preserve = self.preserve_data_check.isChecked()
        domain = self.domain_input.text().strip()
        if mode == "install":
            comps_arg = ",".join(comps) if comps else ",".join(["postgres","redis","nginx","python"])
            cmd = f"python -m tools.installer.cli install --domain {domain} --components {comps_arg}{' --dry-run' if dry else ''}"
        else:
            cmd = f"python -m tools.installer.cli uninstall{' --preserve-data' if preserve else ''}{' --dry-run' if dry else ''}"
        self._append_output("CLI command", {"cmd": cmd})
        QMessageBox.information(self, "CLI", cmd)

    def _on_run(self):
        domain = self.domain_input.text().strip()
        if not self._validate_domain(domain):
            QMessageBox.warning(self, "Invalid Domain", "Please enter a valid domain (e.g., example.com) or 'localhost'.")
            return
        comps = self._selected_components(); dry = self.dry_run_check.isChecked()
        mode = "install" if self.install_radio.isChecked() else "uninstall"
        comps_resolved, notes = self._resolve_dependencies(comps, mode)
        for n in notes: self._append_output("Dependency: " + n)
        if not is_admin(): self._append_output("Warning: not running as administrator. Some actions may fail. Attempting elevation when needed.")
        offline = False
        try:
            import urllib.request
            urllib.request.urlopen("https://www.microsoft.com", timeout=2)
        except Exception:
            offline = True
        if offline:
            self._append_output("Offline mode detected: installer will attempt local/cache-based operations where possible.")
        self.btn_action.setEnabled(False); self.btn_cancel.setEnabled(True); self.progress.setValue(0)
        self._progress_per_component = {c: 0 for c in comps_resolved}
        self._progress_total = len(comps_resolved) * 4 if comps_resolved else 1
        try:
            max_retries = int(getattr(self, 'retry_count', QLineEdit("0")).text() or "0")
            backoff_ms = int(getattr(self, 'backoff_ms', QLineEdit("0")).text() or "0")
        except Exception:
            max_retries = 0; backoff_ms = 0
        if mode == "install":
            self._append_output(f"Starting {'dry-run ' if dry else ''}install for components: {comps_resolved}")
            self.thread = QThread(); self.worker = Worker(install_all, domain, comps_resolved, True, dry, _max_retries=max_retries, _backoff_ms=backoff_ms)
        else:
            preserve = self.preserve_data_check.isChecked()
            self._append_output(f"Starting {'dry-run ' if dry else ''}uninstall (preserve_data={preserve}) for components: {comps_resolved}")
            self.thread = QThread(); self.worker = Worker(uninstall_all, preserve, dry, comps_resolved, _max_retries=max_retries, _backoff_ms=backoff_ms)
        self.worker.moveToThread(self.thread)
        self.worker.progress.connect(self._on_step_progress)
        self.worker.finished.connect(lambda res: self._on_finished_with_health(res, comps_resolved))
        self.worker.error.connect(self._on_error)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def _on_step_progress(self, step, component, meta):
        self._append_output(f"[{component}] {step}", {"component": component, "step": step, "meta": meta})
        if component:
            self._progress_per_component[component] = self._progress_per_component.get(component, 0) + 1
        done_steps = sum(self._progress_per_component.values())
        pct = int((done_steps / max(self._progress_total, 1)) * 100)
        self.progress.setValue(min(100, pct))

    def _health_checks(self, components):
        results = {}
        if "redis" in components:
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(1)
                s.connect(("127.0.0.1", int(self.redis_port.text() or 6379)))
                s.sendall(b"PING\r\n"); data = s.recv(16); results["redis"] = data.startswith(b"+PONG"); s.close()
            except Exception:
                results["redis"] = False
        if "nginx" in components:
            import http.client
            try:
                port = int(self.nginx_port.text() or 80)
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
                conn.request("GET", "/"); resp = conn.getresponse(); results["nginx"] = (resp.status < 500); conn.close()
            except Exception:
                results["nginx"] = False
        if "postgres" in components:
            try:
                import psycopg2  # type: ignore
                user = self.db_user.text() or "postgres"; pw = self.db_pass.text() or None
                conn = psycopg2.connect(host="127.0.0.1", port=5432, user=user, password=pw or "", connect_timeout=1)
                cur = conn.cursor(); cur.execute("SELECT 1"); cur.fetchone(); conn.close(); results["postgres"] = True
            except Exception:
                try:
                    import socket
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(1)
                    rc = s.connect_ex(("127.0.0.1", 5432)); s.close(); results["postgres"] = (rc == 0)
                except Exception:
                    results["postgres"] = False
        if "python" in components:
            results["python"] = True
        return results

    def _on_finished_with_health(self, res, components):
        self.progress.setValue(100)
        self._append_output("Operation finished", res)
        if self.install_radio.isChecked():
            is_dry_run = isinstance(res, dict) and res.get("status") == "dry-run"
            if not is_dry_run:
                hc = self._health_checks(components)
                self._append_output("Health checks completed", hc)
                QMessageBox.information(self, "Health Checks", json.dumps(hc, indent=2))
        QMessageBox.information(self, "Result", json.dumps(res, indent=2))
        self._cleanup_thread()

    def _service_action(self, action):
        item = self.services_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Services", "Select a component first")
            return
        comp = item.text(); ok = False
        if action == "start": ok = bool(start_component_service(comp))
        elif action == "stop": ok = bool(stop_component_service(comp))
        elif action == "restart": stop_component_service(comp); ok = bool(start_component_service(comp))
        elif action == "status":
            status = None
            try:
                import socket
                port_map = {"redis": int(self.redis_port.text() or 6379), "nginx": int(self.nginx_port.text() or 80), "postgres": 5432}
                if comp in port_map:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(0.5)
                    rc = s.connect_ex(("127.0.0.1", port_map[comp])); s.close(); status = (rc == 0)
                else:
                    status = True
            except Exception:
                status = None
            self._append_output(f"Service status for {comp}: {status}", {"service_action": "status", "component": comp, "status": status})
            QMessageBox.information(self, "Service Status", f"{comp}: {'running' if status else 'stopped' if status is False else 'unknown'}")
            return
        self._append_output(f"Service {action} for {comp}: {'ok' if ok else 'failed'}", {"service_action": action, "component": comp, "ok": ok})

    def _on_cancel(self):
        try:
            if hasattr(self, 'worker') and self.worker: self.worker.cancel()
            if hasattr(self, 'thread') and self.thread: self.thread.quit(); self.thread.wait()
            self._append_output("Operation cancelled by user.")
        except Exception:
            pass
        finally:
            self.btn_action.setEnabled(True); self.btn_cancel.setEnabled(False); self.progress.setValue(0)

    def _on_error(self, err):
        hint = ""
        if "permission" in err.lower() or "admin" in err.lower(): hint = "\nHint: Try running as administrator or ensure elevation is allowed."
        elif "not found" in err.lower() or "missing" in err.lower(): hint = "\nHint: Check system dependencies and PATH settings."
        self._append_output("Error: " + err + hint, {"error": err})
        QMessageBox.critical(self, "Error", err + hint)
        self._cleanup_thread()

    def _cleanup_thread(self):
        try:
            self.thread.quit(); self.thread.wait()
        except Exception:
            pass
        self.btn_action.setEnabled(True); self.btn_cancel.setEnabled(False)

    def _on_export_log(self):
        default_name = f"installer-log-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
        path, _ = QFileDialog.getSaveFileName(self, "Export Text Log", default_name, "Text Files (*.txt);;All Files (*)")
        if not path: return
        try:
            text = self.output.toPlainText()
            with open(path, "w", encoding="utf-8") as f: f.write(text)
            QMessageBox.information(self, "Export Text Log", f"Log exported to: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Text Log", f"Failed to export log: {e}")

    def _on_export_json_log(self):
        default_name = f"installer-jsonlog-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.jsonl"
        path, _ = QFileDialog.getSaveFileName(self, "Export JSON Log", default_name, "JSON Lines (*.jsonl);;All Files (*)")
        if not path: return
        try:
            if not hasattr(self, '_json_log_file_path') or not self._json_log_file_path or not os.path.exists(self._json_log_file_path):
                QMessageBox.warning(self, "Export JSON Log", "No session JSON log file found.")
                return
            shutil.copyfile(self._json_log_file_path, path)
            QMessageBox.information(self, "Export JSON Log", f"JSON log exported to: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export JSON Log", f"Failed to export JSON log: {e}")


def run_gui():
    if _gui_import_error:
        print("PySide6 import failed:", _gui_import_error)
        print("Install with: pip install PySide6")
        return
    app = QApplication(sys.argv)
    w = InstallerWindow(); w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    run_gui()
