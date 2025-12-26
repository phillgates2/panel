"""Simple PySide6 GUI PoC for the installer.

Install requirement for GUI PoC: `pip install PySide6`
"""
import sys
import logging

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QPushButton, QMessageBox, QCheckBox, QRadioButton
    )
except Exception as e:
    # GUI isn't available in headless CI; provide helpful message when run
    PySide6 = None
    _gui_import_error = e
else:
    _gui_import_error = None

from .core import install_all, uninstall_all
from PySide6.QtCore import QObject, Signal, Slot, QThread
from PySide6.QtWidgets import QTextEdit

log = logging.getLogger(__name__)


class Worker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    @Slot()
    def run(self):
        try:
            res = self.func(*self.args, **self.kwargs)
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))


class InstallerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Panel Installer (PoC)")
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        v = QVBoxLayout()

        h = QHBoxLayout()
        h.addWidget(QLabel("Domain:"))
        self.domain_input = QLineEdit("localhost")
        h.addWidget(self.domain_input)
        v.addLayout(h)

        self.chk_postgres = QCheckBox("Postgres")
        self.chk_postgres.setChecked(True)
        self.chk_redis = QCheckBox("Redis")
        self.chk_redis.setChecked(True)
        self.chk_nginx = QCheckBox("Nginx")
        self.chk_nginx.setChecked(True)
        self.chk_python = QCheckBox("Python Env")
        self.chk_python.setChecked(True)

        v.addWidget(self.chk_postgres)
        v.addWidget(self.chk_redis)
        v.addWidget(self.chk_nginx)
        v.addWidget(self.chk_python)

        self.install_radio = QRadioButton("Install")
        self.install_radio.setChecked(True)
        self.uninstall_radio = QRadioButton("Uninstall")
        v.addWidget(self.install_radio)
        v.addWidget(self.uninstall_radio)

        opt_h = QHBoxLayout()
        self.dry_run_check = QCheckBox("Dry-run (show commands only)")
        opt_h.addWidget(self.dry_run_check)
        v.addLayout(opt_h)

        self.btn_action = QPushButton("Run")
        self.btn_action.clicked.connect(self._on_run)
        v.addWidget(self.btn_action)

        self.btn_rollback = QPushButton("Manage Rollback")
        self.btn_rollback.clicked.connect(self._on_manage_rollback)
        v.addWidget(self.btn_rollback)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        v.addWidget(self.output)

        root.setLayout(v)
        self.setCentralWidget(root)

    def _append_output(self, text):
        self.output.append(text)

    def _on_run(self):
        domain = self.domain_input.text().strip()
        comps = []
        if self.chk_postgres.isChecked():
            comps.append("postgres")
        if self.chk_redis.isChecked():
            comps.append("redis")
        if self.chk_nginx.isChecked():
            comps.append("nginx")
        if self.chk_python.isChecked():
            comps.append("python")

        dry = self.dry_run_check.isChecked()

        # Disable UI while running
        self.btn_action.setEnabled(False)
        self._append_output(f"Starting {'dry-run ' if dry else ''}operation for components: {comps}")

        # Run installer in background
        self.thread = QThread()
        self.worker = Worker(install_all, domain, comps, True, dry)
        self.worker.moveToThread(self.thread)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def _on_manage_rollback(self):
        # Show current recorded state and offer dry-run, run, or retry
        from .state import read_state, rollback
        state = read_state()
        actions = state.get('actions', [])
        if not actions:
            QMessageBox.information(self, "Rollback", "No recorded install actions found.")
            return

        txt = "Recorded actions (oldest -> newest):\n" + "\n".join([f"- {a.get('component')}" for a in actions])
        choice = QMessageBox.question(self, "Rollback", txt + "\n\nRun a dry-run rollback?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        if choice == QMessageBox.StandardButton.Cancel:
            return
        if choice == QMessageBox.StandardButton.Yes:
            self._append_output("Performing dry-run rollback...")
            res = rollback(preserve_data=True, dry_run=True)
            self._append_output("Dry-run results:\n" + str(res))
            QMessageBox.information(self, "Dry-run complete", str(res))
            return

        # If user clicked No, offer to run real rollback or retry failed only
        run_choice = QMessageBox.question(self, "Rollback", "Execute rollback now (this will attempt to uninstall recorded components)?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if run_choice == QMessageBox.StandardButton.Yes:
            self._append_output("Executing rollback...")
            res = rollback(preserve_data=True, dry_run=False)
            self._append_output("Rollback results:\n" + str(res))
            QMessageBox.information(self, "Rollback complete", str(res))
            return
        else:
            # Offer a retry option that simply runs rollback again (failed items remain in state)
            retry_choice = QMessageBox.question(self, "Retry", "Retry failed actions only? (will attempt uninstall for remaining actions)", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if retry_choice == QMessageBox.StandardButton.Yes:
                self._append_output("Retrying failed actions...")
                res = rollback(preserve_data=True, dry_run=False)
                self._append_output("Retry results:\n" + str(res))
                QMessageBox.information(self, "Retry complete", str(res))
                return
            else:
                return

    def _on_finished(self, res):
        self._append_output("Operation finished:\n" + str(res))
        QMessageBox.information(self, "Result", str(res))
        self._cleanup_thread()

    def _on_error(self, err):
        self._append_output("Error: " + err)
        QMessageBox.critical(self, "Error", err)
        self._cleanup_thread()

    def _cleanup_thread(self):
        try:
            self.thread.quit()
            self.thread.wait()
        except Exception:
            pass
        self.btn_action.setEnabled(True)


def run_gui():
    if _gui_import_error:
        print("PySide6 import failed:", _gui_import_error)
        print("Install with: pip install PySide6")
        return

    app = QApplication(sys.argv)
    w = InstallerWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    run_gui()
