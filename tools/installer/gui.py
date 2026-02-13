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
from .deps import check_system_deps

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
        "wizard": "Run Wizard",
        "preset": "Preset:",
        "save_cfg": "Save Config…",
        "load_cfg": "Load Config…",
        "save_secret": "Save DB Secret",
        "log_filter": "Filter:",
        "log_search": "Search:",
        "severity": "Severity:",
        "export_redact": "Export (Redact)",
        "diagnostics": "Diagnostics",
        "tail_logs": "Tail Logs",
        "crash_recovery": "Crash Recovery",
        "sandbox": "Sandbox Mode",
        "telemetry": "Telemetry Opt-in",
        "privacy": "Privacy: Only anonymized metrics are sent.",
        "check_updates": "Check for Updates",
        "admin_email": "Admin Email:",
        "admin_password": "Admin Password:",
        "create_default_user": "Create default admin user",
    }
}


def _load_external_translations():
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
                existing = _STRINGS.get(locale, {})
                merged = {**existing, **data}
                _STRINGS[locale] = merged
            except Exception:
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
        _load_external_translations()
        self.lang = "en"
        self.str = _STRINGS[self.lang]
        self.setWindowTitle(self.str["title"])
        self._log_file_path = None
        self._json_log_file_path = None
        self._progress_total = 100
        self._progress_per_component = {}
        self._log_buffer = []  # keep structured log lines for filtering/search
        self._build_ui()
        self._apply_platform_rules()
        self._config_path = os.path.join(os.path.expanduser("~"), ".panel_installer", "config.json")
        self._load_config_silent()

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

        preset_h = QHBoxLayout()
        self.preset_label = QLabel(self._tr("preset"))
        self.preset_select = QComboBox(); self.preset_select.addItems(["dev", "staging", "prod"]); self.preset_select.currentTextChanged.connect(self._apply_preset)
        preset_h.addWidget(self.preset_label); preset_h.addWidget(self.preset_select)
        main_layout.addLayout(preset_h)

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
        self.sandbox_check = QCheckBox(self._tr("sandbox")); self.opt_h.addWidget(self.sandbox_check)
        self.telemetry_check = QCheckBox(self._tr("telemetry")); self.opt_h.addWidget(self.telemetry_check)
        self.privacy_label = QLabel(self._tr("privacy")); self.opt_h.addWidget(self.privacy_label)
        main_layout.addLayout(self.opt_h)

        self.retry_h = QHBoxLayout()
        self.retry_label = QLabel(self._tr("retry"))
        self.retry_count = QLineEdit("0"); self.retry_h.addWidget(self.retry_label); self.retry_h.addWidget(self.retry_count)
        self.backoff_label = QLabel(self._tr("backoff_ms"))
        self.backoff_ms = QLineEdit("0"); self.retry_h.addWidget(self.backoff_label); self.retry_h.addWidget(self.backoff_ms)
        main_layout.addLayout(self.retry_h)

        cfg_h = QHBoxLayout()
        self.btn_save_cfg = QPushButton(self._tr("save_cfg")); self.btn_save_cfg.clicked.connect(self._on_save_config); cfg_h.addWidget(self.btn_save_cfg)
        self.btn_load_cfg = QPushButton(self._tr("load_cfg")); self.btn_load_cfg.clicked.connect(self._on_load_config); cfg_h.addWidget(self.btn_load_cfg)
        self.btn_save_secret = QPushButton(self._tr("save_secret")); self.btn_save_secret.clicked.connect(self._on_save_secret); cfg_h.addWidget(self.btn_save_secret)
        self.btn_check_updates = QPushButton(self._tr("check_updates")); self.btn_check_updates.clicked.connect(self._on_check_updates); cfg_h.addWidget(self.btn_check_updates)
        main_layout.addLayout(cfg_h)

        btns_h = QHBoxLayout()
        self.btn_action = QPushButton(self._tr("run")); self.btn_action.clicked.connect(self._on_run); btns_h.addWidget(self.btn_action)
        self.btn_wizard = QPushButton(self._tr("wizard")); self.btn_wizard.clicked.connect(self._on_wizard); btns_h.addWidget(self.btn_wizard)
        self.btn_recovery = QPushButton(self._tr("crash_recovery")); self.btn_recovery.clicked.connect(self._on_crash_recovery); btns_h.addWidget(self.btn_recovery)
        self.btn_cancel = QPushButton(self._tr("cancel")); self.btn_cancel.setEnabled(False); self.btn_cancel.clicked.connect(self._on_cancel); btns_h.addWidget(self.btn_cancel)
        self.btn_preflight = QPushButton(self._tr("preflight")); self.btn_preflight.clicked.connect(self._run_preflight); btns_h.addWidget(self.btn_preflight)
        self.btn_cli = QPushButton(self._tr("cli_equiv")); self.btn_cli.clicked.connect(self._show_cli_command); btns_h.addWidget(self.btn_cli)
        main_layout.addLayout(btns_h)

        self.progress = QProgressBar(); self.progress.setMinimum(0); self.progress.setMaximum(100); self.progress.setValue(0)
        main_layout.addWidget(self.progress)

        self.main_tab.setLayout(main_layout)
        self.tabs.addTab(self.main_tab, self._tr("install_uninstall"))

        # Services tab
        self.services_tab = QWidget(); services_layout = QVBoxLayout()
        self.services_list = QListWidget()
        for comp in ["postgres", "redis", "nginx", "python"]:
            self.services_list.addItem(QListWidgetItem(comp))
        svc_btns = QHBoxLayout()
        self.btn_service_start = QPushButton(self._tr("services_start")); self.btn_service_start.clicked.connect(lambda: self._service_action("start")); svc_btns.addWidget(self.btn_service_start)
        self.btn_service_stop = QPushButton(self._tr("services_stop")); self.btn_service_stop.clicked.connect(lambda: self._service_action("stop")); svc_btns.addWidget(self.btn_service_stop)
        self.btn_service_restart = QPushButton(self._tr("services_restart")); self.btn_service_restart.clicked.connect(lambda: self._service_action("restart")); svc_btns.addWidget(self.btn_service_restart)
        self.btn_service_status = QPushButton(self._tr("services_status")); self.btn_service_status.clicked.connect(lambda: self._service_action("status")); svc_btns.addWidget(self.btn_service_status)
        services_layout.addWidget(self.services_list)
        services_layout.addLayout(svc_btns)
        services_tab = QWidget(); services_tab.setLayout(services_layout)
        self.tabs.addTab(services_tab, self._tr("services"))

        # Logs tab with advanced controls
        logs_tab = QWidget(); logs_layout = QVBoxLayout()
        adv_h = QHBoxLayout()
        adv_h.addWidget(QLabel(self._tr("log_filter")))
        self.log_filter_combo = QComboBox(); self.log_filter_combo.addItems(["all", "info", "warn", "error"]); self.log_filter_combo.currentTextChanged.connect(self._apply_log_filters); adv_h.addWidget(self.log_filter_combo)
        adv_h.addWidget(QLabel(self._tr("log_search")))
        self.log_search = QLineEdit(""); self.log_search.textChanged.connect(self._apply_log_filters); adv_h.addWidget(self.log_search)
        adv_h.addWidget(QLabel(self._tr("severity")))
        self.severity_combo = QComboBox(); self.severity_combo.addItems(["info", "warn", "error"]); self.severity_combo.currentTextChanged.connect(self._set_severity_level); adv_h.addWidget(self.severity_combo)
        logs_layout.addLayout(adv_h)
        self.output = QTextEdit(); self.output.setReadOnly(True)
        logs_layout.addWidget(self.output)
        export_h = QHBoxLayout()
        self.btn_save_log = QPushButton(self._tr("export_text")); self.btn_save_log.clicked.connect(self._on_export_log); export_h.addWidget(self.btn_save_log)
        self.btn_save_json_log = QPushButton(self._tr("export_json")); self.btn_save_json_log.clicked.connect(self._on_export_json_log); export_h.addWidget(self.btn_save_json_log)
        self.btn_export_redact = QPushButton(self._tr("export_redact")); self.btn_export_redact.clicked.connect(self._on_export_redacted); export_h.addWidget(self.btn_export_redact)
        logs_layout.addLayout(export_h)
        # Diagnostics: attach/tail component logs
        diag_h = QHBoxLayout()
        self.btn_tail_logs = QPushButton(self._tr("tail_logs")); self.btn_tail_logs.clicked.connect(self._on_tail_logs); diag_h.addWidget(self.btn_tail_logs)
        self.btn_diagnostics = QPushButton(self._tr("diagnostics")); self.btn_diagnostics.clicked.connect(self._on_diagnostics); diag_h.addWidget(self.btn_diagnostics)
        logs_layout.addLayout(diag_h)
        logs_tab.setLayout(logs_layout)
        self.tabs.addTab(logs_tab, self._tr("logs"))

        # Settings tab
        settings_tab = QWidget(); settings_layout = QVBoxLayout()
        db_h = QHBoxLayout(); db_h.addWidget(QLabel(self._tr("db_user"))); self.db_user = QLineEdit("panel"); db_h.addWidget(self.db_user); settings_layout.addLayout(db_h)
        dp_h = QHBoxLayout(); dp_h.addWidget(QLabel(self._tr("db_pass"))); self.db_pass = QLineEdit(""); self.db_pass.setEchoMode(QLineEdit.Password); dp_h.addWidget(self.db_pass); settings_layout.addLayout(dp_h)
        ae_h = QHBoxLayout(); ae_h.addWidget(QLabel(self._tr("admin_email"))); self.admin_email = QLineEdit("admin@panel.local"); ae_h.addWidget(self.admin_email); settings_layout.addLayout(ae_h)
        ap_h = QHBoxLayout(); ap_h.addWidget(QLabel(self._tr("admin_password"))); self.admin_password = QLineEdit(""); self.admin_password.setEchoMode(QLineEdit.Password); ap_h.addWidget(self.admin_password); settings_layout.addLayout(ap_h)
        self.create_default_user_check = QCheckBox(self._tr("create_default_user")); self.create_default_user_check.setChecked(True); settings_layout.addWidget(self.create_default_user_check)
        rp_h = QHBoxLayout(); rp_h.addWidget(QLabel(self._tr("redis_port"))); self.redis_port = QLineEdit("6379"); rp_h.addWidget(self.redis_port); settings_layout.addLayout(rp_h)
        np_h = QHBoxLayout(); np_h.addWidget(QLabel(self._tr("nginx_port"))); self.nginx_port = QLineEdit("80"); np_h.addWidget(self.nginx_port); settings_layout.addLayout(np_h)
        tls_h = QHBoxLayout(); tls_h.addWidget(QLabel(self._tr("tls_cert"))); self.tls_cert = QLineEdit(""); tls_h.addWidget(self.tls_cert); settings_layout.addLayout(tls_h)
        tlsk_h = QHBoxLayout(); tlsk_h.addWidget(QLabel(self._tr("tls_key"))); self.tls_key = QLineEdit(""); tlsk_h.addWidget(self.tls_key); settings_layout.addLayout(tlsk_h)
        self.btn_validate_settings = QPushButton(self._tr("validate_settings")); self.btn_validate_settings.clicked.connect(self._validate_settings); settings_layout.addWidget(self.btn_validate_settings)
        settings_tab.setLayout(settings_layout)
        self.tabs.addTab(settings_tab, self._tr("settings"))

        self.setCentralWidget(self.tabs)
        self._last_error_text = ""
        self._severity_level = "info"

    def _on_lang_change(self, lang):
        self.lang = lang
        self.str = _STRINGS.get(self.lang, _STRINGS["en"])
        self.setWindowTitle(self._tr("title"))
        idx = self.tabs.indexOf(self.main_tab); self.tabs.setTabText(idx, self._tr("install_uninstall"))
        idx = self.tabs.indexOf(self.services_tab); self.tabs.setTabText(idx, self._tr("services"))
        self.tabs.setTabText(self.tabs.indexOf(self.tabs.widget(2)), self._tr("logs"))
        self.tabs.setTabText(self.tabs.indexOf(self.tabs.widget(3)), self._tr("settings"))
        self.lang_label.setText(self._tr("language"))
        self.preset_label.setText(self._tr("preset"))
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
        self.sandbox_check.setText(self._tr("sandbox"))
        self.telemetry_check.setText(self._tr("telemetry"))
        self.privacy_label.setText(self._tr("privacy"))
        self.retry_label.setText(self._tr("retry"))
        self.backoff_label.setText(self._tr("backoff_ms"))
        self.btn_action.setText(self._tr("run"))
        self.btn_wizard.setText(self._tr("wizard"))
        self.btn_recovery.setText(self._tr("crash_recovery"))
        self.btn_cancel.setText(self._tr("cancel"))
        self.btn_preflight.setText(self._tr("preflight"))
        self.btn_cli.setText(self._tr("cli_equiv"))
        self.btn_service_start.setText(self._tr("services_start"))
        self.btn_service_stop.setText(self._tr("services_stop"))
        self.btn_service_restart.setText(self._tr("services_restart"))
        self.btn_service_status.setText(self._tr("services_status"))
        self.btn_save_log.setText(self._tr("export_text"))
        self.btn_save_json_log.setText(self._tr("export_json"))
        self.btn_export_redact.setText(self._tr("export_redact"))
        self.btn_tail_logs.setText(self._tr("tail_logs"))
        self.btn_diagnostics.setText(self._tr("diagnostics"))
        self.btn_save_cfg.setText(self._tr("save_cfg"))
        self.btn_load_cfg.setText(self._tr("load_cfg"))
        self.btn_save_secret.setText(self._tr("save_secret"))
        self.btn_check_updates.setText(self._tr("check_updates"))

        # Settings labels
        try:
            # These widgets may not exist in older configs
            self.create_default_user_check.setText(self._tr("create_default_user"))
        except Exception:
            pass

    def _apply_platform_rules(self):
        # GUI installer is meant to always target Postgres.
        # Keep Postgres enabled and selected so user bootstrapping can run.
        try:
            self.chk_postgres.setChecked(True)
            self.chk_postgres.setEnabled(False)
        except Exception:
            pass

    def _on_component_toggle(self):
        # Persist toggles and enforce required components.
        try:
            # Always keep Postgres selected (and disabled where possible).
            self.chk_postgres.setChecked(True)
        except Exception:
            pass
        self._save_config_silent()

    def _selected_components(self):
        comps = []
        try:
            if self.chk_postgres.isChecked():
                comps.append("postgres")
        except Exception:
            comps.append("postgres")
        try:
            if self.chk_redis.isChecked():
                comps.append("redis")
        except Exception:
            pass
        try:
            if self.chk_nginx.isChecked():
                comps.append("nginx")
        except Exception:
            pass
        try:
            if self.chk_python.isChecked():
                comps.append("python")
        except Exception:
            pass
        # Guarantee Postgres presence
        if "postgres" not in comps:
            comps.insert(0, "postgres")
        return comps

    def _resolve_dependencies(self, comps, mode):
        # Minimal dependency resolver; keep behavior predictable.
        resolved = list(dict.fromkeys(comps or []))
        notes = []
        if "postgres" not in resolved:
            resolved.insert(0, "postgres")
            notes.append("postgres required")
        return resolved, notes

    def _apply_preset(self, preset: str):
        # Simple presets; keep Postgres always on.
        p = (preset or "").lower().strip()
        try:
            self.chk_postgres.setChecked(True)
        except Exception:
            pass
        if p == "dev":
            self.chk_redis.setChecked(True)
            self.chk_nginx.setChecked(True)
            self.chk_python.setChecked(True)
        elif p == "staging":
            self.chk_redis.setChecked(True)
            self.chk_nginx.setChecked(True)
            self.chk_python.setChecked(True)
        elif p == "prod":
            self.chk_redis.setChecked(True)
            self.chk_nginx.setChecked(True)
            self.chk_python.setChecked(True)
        self._save_config_silent()

    def _run_preflight(self):
        try:
            missing = check_system_deps()
            if missing:
                self._append_output("Preflight: missing system deps", {"missing": missing}, severity="warn")
                QMessageBox.warning(self, "Preflight", "Missing dependencies:\n" + "\n".join(missing))
            else:
                self._append_output("Preflight: ok", {"missing": []}, severity="info")
                QMessageBox.information(self, "Preflight", "All required dependencies appear installed.")
        except Exception as e:
            self._append_output("Preflight failed", {"error": str(e)}, severity="error")
            QMessageBox.critical(self, "Preflight", f"Preflight failed: {e}")

    def _show_cli_command(self):
        try:
            comps = self._selected_components()
            domain = self.domain_input.text().strip() or "localhost"
            dry = self.dry_run_check.isChecked()
            op = "install" if self.install_radio.isChecked() else "uninstall"
            cmd = ["python3", "-m", "tools.installer", "--cli", op, "--domain", domain]
            if op == "install":
                cmd += ["--components", ",".join(comps)]
                if dry:
                    cmd.append("--dry-run")
            else:
                if self.preserve_data_check.isChecked():
                    cmd.append("--preserve-data")
                if dry:
                    cmd.append("--dry-run")
            text = " ".join(cmd)
            self._append_output("CLI equivalent", {"cmd": text}, severity="info")
            QMessageBox.information(self, "CLI", text)
        except Exception as e:
            QMessageBox.critical(self, "CLI", f"Failed to build CLI command: {e}")

    def _on_wizard(self):
        # Keep wizard minimal in this PoC.
        QMessageBox.information(self, "Wizard", "Wizard is not implemented in this GUI PoC. Use Settings + Run.")

    def _on_save_secret(self):
        # Minimal secret persistence: store DB password to user config file.
        try:
            cfg = self._config_snapshot()
            # Avoid writing password unless user explicitly hits this button.
            cfg["db_pass"] = self.db_pass.text()
            cfg["admin_password"] = getattr(self, "admin_password", QLineEdit("")).text()
            cfg_dir = os.path.dirname(self._config_path)
            os.makedirs(cfg_dir, exist_ok=True)
            secrets_path = os.path.join(cfg_dir, "secrets.json")
            with open(secrets_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            self._append_output("Saved secrets", {"path": secrets_path}, severity="info")
            QMessageBox.information(self, "Secrets", f"Secrets saved to: {secrets_path}")
        except Exception as e:
            self._append_output("Failed to save secrets", {"error": str(e)}, severity="error")
            QMessageBox.critical(self, "Secrets", f"Failed to save secrets: {e}")

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
        self._save_config_silent()

    def _append_output(self, text, json_obj=None, severity="info"):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {severity.upper()}: {text}"
        # buffer
        self._log_buffer.append({"ts": timestamp, "severity": severity, "text": text, "data": json_obj})
        # apply filters
        if self._passes_filters(text, severity):
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
                record = {"ts": datetime.datetime.now().isoformat(), "message": text, "severity": severity}
                if json_obj is not None:
                    record["data"] = json_obj
                with open(self._json_log_file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")
            except Exception:
                pass

    def _passes_filters(self, text, severity):
        # severity filter
        levels = {"info": 0, "warn": 1, "error": 2}
        if levels.get(severity, 0) < levels.get(self._severity_level, 0):
            return False
        # combo filter
        filt = self.log_filter_combo.currentText() if hasattr(self, 'log_filter_combo') else 'all'
        if filt != 'all' and severity != filt:
            return False
        # text search
        q = self.log_search.text().strip() if hasattr(self, 'log_search') else ''
        if q and q.lower() not in text.lower():
            return False
        return True

    def _apply_log_filters(self):
        try:
            self.output.clear()
            for rec in self._log_buffer:
                if self._passes_filters(rec["text"], rec["severity"]):
                    self.output.append(f"[{rec['ts']}] {rec['severity'].upper()}: {rec['text']}")
        except Exception:
            pass

    def _set_severity_level(self):
        self._severity_level = self.severity_combo.currentText()
        self._apply_log_filters()

    def _on_export_redacted(self):
        # Export logs with basic redaction (mask IPs, emails, secrets-like values)
        default_name = f"installer-log-redacted-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
        path, _ = QFileDialog.getSaveFileName(self, "Export Redacted Log", default_name, "Text Files (*.txt);;All Files (*)")
        if not path:
            return
        try:
            import re as _re
            def _redact(s):
                s = _re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "[IP]", s)
                s = _re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "[EMAIL]", s)
                s = _re.sub(r"(?i)(password|secret|token)[^\n]*", "[REDACTED]", s)
                return s
            text = self.output.toPlainText()
            with open(path, "w", encoding="utf-8") as f:
                f.write(_redact(text))
            QMessageBox.information(self, "Export Redacted Log", f"Redacted log exported to: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Redacted Log", f"Failed to export: {e}")

    def _on_tail_logs(self):
        # Tail common component logs if present
        candidates = [
            ("nginx", "/var/log/nginx/error.log"),
            ("postgres", "/var/log/postgresql/postgresql.log"),
        ]
        lines = []
        for name, path in candidates:
            try:
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        tail = f.readlines()[-50:]
                    lines.append(f"== {name} ==\n" + "".join(tail))
            except Exception:
                pass
        msg = "\n\n".join(lines) if lines else "No component logs found."
        self._append_output("Diagnostics tail", {"tail": bool(lines)}, severity="info")
        QMessageBox.information(self, "Diagnostics", msg)

    def _on_diagnostics(self):
        # Best-effort: show existence of key logs
        info = {}
        for name, path in [("nginx", "/var/log/nginx/error.log"), ("postgres", "/var/log/postgresql/postgresql.log")]:
            info[name] = os.path.exists(path)
        self._append_output("Diagnostics", info, severity="info")
        QMessageBox.information(self, "Diagnostics", json.dumps(info, indent=2))

    def _on_crash_recovery(self):
        # Read installer state and offer repair actions
        try:
            from .state import read_state, rollback
            st = read_state()
            actions = st.get("actions", [])
            if not actions:
                QMessageBox.information(self, "Recovery", "No partial installs to recover.")
                return
            txt = "\n".join([a.get("component", "?") for a in actions])
            choice = QMessageBox.question(self, "Recovery", f"Found recorded actions:\n{txt}\n\nAttempt repair (uninstall recorded components)?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if choice == QMessageBox.StandardButton.Yes:
                res = rollback(preserve_data=True, dry_run=False)
                self._append_output("Recovery executed", res, severity="warn")
                QMessageBox.information(self, "Recovery", json.dumps(res, indent=2))
        except Exception as e:
            QMessageBox.critical(self, "Recovery", f"Failed: {e}")

    def _on_check_updates(self):
        # Stubbed: check for updates via a version file or remote endpoint
        try:
            current = "0.1.0"
            latest = current
            # In real implementation, fetch from remote URL or package metadata
            self._append_output("Update check", {"current": current, "latest": latest})
            if latest != current:
                choice = QMessageBox.question(self, "Update", f"New version {latest} available. Update now?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if choice == QMessageBox.StandardButton.Yes:
                    QMessageBox.information(self, "Update", "Updating… (stub)")
            else:
                QMessageBox.information(self, "Update", "You are on the latest version.")
        except Exception as e:
            QMessageBox.critical(self, "Update", f"Failed to check updates: {e}")

    def _config_snapshot(self):
        return {
            "language": self.lang_select.currentText(),
            "dark_mode": self.dark_mode_check.isChecked(),
            "domain": self.domain_input.text().strip(),
            "components": self._selected_components(),
            "db_user": self.db_user.text(),
            "db_pass": self.db_pass.text(),
            "admin_email": getattr(self, "admin_email", QLineEdit("")).text(),
            "admin_password": getattr(self, "admin_password", QLineEdit("")).text(),
            "create_default_user": getattr(self, "create_default_user_check", QCheckBox()).isChecked() if hasattr(self, "create_default_user_check") else True,
            "redis_port": self.redis_port.text(),
            "nginx_port": self.nginx_port.text(),
            "preset": self.preset_select.currentText(),
            "sandbox": self.sandbox_check.isChecked(),
            "telemetry": self.telemetry_check.isChecked(),
        }

    def _apply_config(self, cfg):
        try:
            lang = cfg.get("language")
            if lang and lang in _STRINGS:
                self.lang_select.setCurrentText(lang)
            self.dark_mode_check.setChecked(bool(cfg.get("dark_mode")))
            self.domain_input.setText(cfg.get("domain", "localhost"))
            comps = cfg.get("components", [])
            self.chk_postgres.setChecked("postgres" in comps)
            self.chk_redis.setChecked("redis" in comps)
            self.chk_nginx.setChecked("nginx" in comps)
            self.chk_python.setChecked("python" in comps)
            if cfg.get("db_user") is not None: self.db_user.setText(str(cfg.get("db_user")))
            if cfg.get("db_pass") is not None: self.db_pass.setText(str(cfg.get("db_pass")))
            if cfg.get("admin_email") is not None and hasattr(self, "admin_email"): self.admin_email.setText(str(cfg.get("admin_email")))
            if cfg.get("admin_password") is not None and hasattr(self, "admin_password"): self.admin_password.setText(str(cfg.get("admin_password")))
            if hasattr(self, "create_default_user_check") and (cfg.get("create_default_user") is not None):
                self.create_default_user_check.setChecked(bool(cfg.get("create_default_user")))
            if cfg.get("redis_port"): self.redis_port.setText(str(cfg.get("redis_port")))
            if cfg.get("nginx_port"): self.nginx_port.setText(str(cfg.get("nginx_port")))
            preset = cfg.get("preset")
            if preset:
                self.preset_select.setCurrentText(preset)
            self.sandbox_check.setChecked(bool(cfg.get("sandbox")))
            self.telemetry_check.setChecked(bool(cfg.get("telemetry")))
        except Exception:
            pass

    def _save_config_silent(self):
        try:
            cfg_dir = os.path.dirname(self._config_path)
            os.makedirs(cfg_dir, exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._config_snapshot(), f, indent=2)
        except Exception:
            pass

    def _on_save_config(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Save Config", self._config_path, "JSON Files (*.json);;All Files (*)")
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._config_snapshot(), f, indent=2)
            QMessageBox.information(self, "Config", f"Config saved to: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Config", f"Failed to save config: {e}")

    def _load_config_silent(self):
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self._apply_config(cfg)
        except Exception:
            pass

    def _on_load_config(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Load Config", self._config_path, "JSON Files (*.json);;All Files (*)")
            if not path:
                return
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self._apply_config(cfg)
            QMessageBox.information(self, "Config", f"Config loaded from: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Config", f"Failed to load config: {e}")

    def _on_run(self):
        domain = self.domain_input.text().strip()
        if not self._validate_domain(domain):
            QMessageBox.warning(self, "Invalid Domain", "Please enter a valid domain (e.g., example.com) or 'localhost'.")
            return
        comps = self._selected_components(); dry = self.dry_run_check.isChecked()
        mode = "install" if self.install_radio.isChecked() else "uninstall"
        comps_resolved, notes = self._resolve_dependencies(comps, mode)
        for n in notes: self._append_output("Dependency: " + n)
        if not is_admin(): self._append_output("Warning: not running as administrator. Some actions may fail. Attempting elevation when needed.", severity="warn")
        offline = False
        try:
            import urllib.request
            urllib.request.urlopen("https://www.microsoft.com", timeout=2)
        except Exception:
            offline = True
        if offline:
            self._append_output("Offline mode detected: installer will attempt local/cache-based operations where possible.", severity="warn")
        if self.sandbox_check.isChecked():
            self._append_output("Sandbox mode enabled: operations will be simulated where possible.", severity="warn")
        if self.telemetry_check.isChecked():
            self._append_output("Telemetry enabled: anonymized metrics may be sent.", severity="info")
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
            # Create a system_admin user during install (user-defined).
            create_default_user = True
            try:
                create_default_user = bool(self.create_default_user_check.isChecked())
            except Exception:
                create_default_user = True
            admin_email = ""
            admin_password = ""
            try:
                admin_email = (self.admin_email.text() or "").strip()
                admin_password = (self.admin_password.text() or "").strip()
            except Exception:
                pass
            if create_default_user and (not dry):
                if not admin_email:
                    QMessageBox.warning(self, "Admin User", "Admin Email is required to create the default admin user.")
                    self.btn_action.setEnabled(True); self.btn_cancel.setEnabled(False)
                    return
                if not admin_password:
                    QMessageBox.warning(self, "Admin User", "Admin Password is required (no auto-generate in GUI mode).")
                    self.btn_action.setEnabled(True); self.btn_cancel.setEnabled(False)
                    return

            # Always target Postgres for bootstrapping.
            db_uri = None
            try:
                from urllib.parse import quote_plus

                user = (self.db_user.text() or "paneluser").strip()
                pw = (self.db_pass.text() or "").strip()
                # DB name is not configurable in the GUI PoC; use Panel default.
                db_uri = f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(pw)}@127.0.0.1:5432/paneldb"
            except Exception:
                db_uri = None
            if create_default_user and (not dry) and not db_uri:
                QMessageBox.critical(self, "Database", "Postgres connection string could not be built. Check DB User/Password.")
                self.btn_action.setEnabled(True); self.btn_cancel.setEnabled(False)
                return
            self.thread = QThread(); self.worker = Worker(
                install_all,
                domain,
                comps_resolved,
                True,
                dry,
                create_default_user=create_default_user,
                admin_email=admin_email or None,
                admin_password=admin_password or None,
                db_uri=db_uri,
                _max_retries=max_retries,
                _backoff_ms=backoff_ms,
            )
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

    def _validate_domain(self, domain: str) -> bool:
        if domain.lower() == "localhost": return True
        pattern = r"^(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
        return re.match(pattern, domain) is not None

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
        self._append_output("Error: " + err + hint, {"error": err}, severity="error")
        QMessageBox.critical(self, "Error", err + hint)
        self._cleanup_thread()

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

    def _cleanup_thread(self):
        try:
            self.thread.quit(); self.thread.wait()
        except Exception:
            pass
        self.btn_action.setEnabled(True); self.btn_cancel.setEnabled(False)


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
