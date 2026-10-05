from __future__ import annotations

import sys
import os
import sqlite3
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from auth_manager import AuthStore
from database import HistoryStore
from engine import detect_bugs
from reports import create_json_report, create_pdf_report, report_as_markdown


DEFAULT_CODE = '''def greet(name):
    return "Hello, " + name

print(greet(user_name))
'''


class AuthDialog(QDialog):
    def __init__(self, auth_store: AuthStore) -> None:
        super().__init__()
        self.auth_store = auth_store
        self.account_email: str | None = None
        self.role: str | None = None
        self.setWindowTitle("Sign in | AI Bug Finder")
        self.setMinimumWidth(620)
        self.setModal(True)

        card = QWidget()
        card.setObjectName("authCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(34, 30, 34, 32)
        card_layout.setSpacing(14)

        brand = QLabel("AI BUG FINDER")
        brand.setObjectName("brandLabel")
        eyebrow = QLabel("YOUR PRIVATE CODE REVIEW WORKSPACE")
        eyebrow.setObjectName("eyebrowLabel")
        title = QLabel("Find bugs before\nthey reach production.")
        title.setObjectName("authTitle")
        subtitle = QLabel(
            "Sign in to review Python issues, inspect safe fix suggestions, "
            "and keep your analysis history together."
        )
        subtitle.setObjectName("mutedLabel")
        subtitle.setWordWrap(True)

        self.auth_tabs = QTabWidget()
        self.auth_tabs.setObjectName("authTabs")
        self.auth_tabs.addTab(self._build_login_tab(), "Sign in")
        self.auth_tabs.addTab(self._build_admin_login_tab(), "Admin login")
        self.auth_tabs.addTab(self._build_registration_tab(), "Create user account")

        card_layout.addWidget(brand)
        card_layout.addWidget(eyebrow)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(4)
        card_layout.addWidget(self.auth_tabs)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 22, 22, 22)
        outer.addWidget(card)

    def _build_login_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 18, 8, 8)
        layout.setSpacing(11)

        layout.addWidget(QLabel("Email address"))
        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText("you@example.com")
        self.login_email.setClearButtonEnabled(True)
        layout.addWidget(self.login_email)

        layout.addWidget(QLabel("Password"))
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Enter your password")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password.returnPressed.connect(self._login)
        layout.addWidget(self.login_password)

        self.show_login_password = QCheckBox("Show password")
        self.show_login_password.toggled.connect(
            lambda visible: self.login_password.setEchoMode(
                QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
            )
        )
        layout.addWidget(self.show_login_password)

        self.login_message = QLabel("")
        self.login_message.setObjectName("formMessage")
        self.login_message.setWordWrap(True)
        layout.addWidget(self.login_message)

        login_button = QPushButton("Sign in")
        login_button.setObjectName("primaryButton")
        login_button.clicked.connect(self._login)
        layout.addWidget(login_button)

        hint = QLabel("New to AI Bug Finder? Create a user account in the next tab.")
        hint.setObjectName("helperLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        return page

    def _build_admin_login_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 18, 8, 8)
        layout.setSpacing(11)

        admin_heading = QLabel("Administrator access")
        admin_heading.setObjectName("workspaceTitle")
        admin_description = QLabel(
            "Sign in with the administrator credentials configured for this app. "
            "Admin accounts cannot be created from user registration."
        )
        admin_description.setObjectName("helperLabel")
        admin_description.setWordWrap(True)
        layout.addWidget(admin_heading)
        layout.addWidget(admin_description)

        layout.addWidget(QLabel("Admin email"))
        self.admin_email_input = QLineEdit(self.auth_store.admin_email)
        self.admin_email_input.setPlaceholderText("Administrator email")
        layout.addWidget(self.admin_email_input)

        layout.addWidget(QLabel("Admin password"))
        self.admin_password_input = QLineEdit()
        self.admin_password_input.setPlaceholderText("Administrator password")
        self.admin_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.admin_password_input.returnPressed.connect(self._admin_login)
        layout.addWidget(self.admin_password_input)

        self.show_admin_password = QCheckBox("Show password")
        self.show_admin_password.toggled.connect(
            lambda visible: self.admin_password_input.setEchoMode(
                QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
            )
        )
        layout.addWidget(self.show_admin_password)

        self.admin_login_message = QLabel("")
        self.admin_login_message.setObjectName("formMessage")
        self.admin_login_message.setWordWrap(True)
        layout.addWidget(self.admin_login_message)

        admin_button = QPushButton("Sign in as administrator")
        admin_button.setObjectName("primaryButton")
        admin_button.clicked.connect(self._admin_login)
        layout.addWidget(admin_button)

        default_hint = QLabel(
            "Admin sign-in is disabled until BUGFINDER_ADMIN_EMAIL and "
            "BUGFINDER_ADMIN_PASSWORD are configured."
        )
        default_hint.setObjectName("helperLabel")
        default_hint.setWordWrap(True)
        layout.addWidget(default_hint)
        return page

    def _build_registration_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 18, 8, 8)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Email address"))
        self.registration_email = QLineEdit()
        self.registration_email.setPlaceholderText("you@example.com")
        self.registration_email.setClearButtonEnabled(True)
        layout.addWidget(self.registration_email)

        layout.addWidget(QLabel("Password"))
        self.registration_password = QLineEdit()
        self.registration_password.setPlaceholderText("At least 8 characters")
        self.registration_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.registration_password)

        layout.addWidget(QLabel("Confirm password"))
        self.confirm_password = QLineEdit()
        self.confirm_password.setPlaceholderText("Enter the same password again")
        self.confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password.returnPressed.connect(self._register)
        layout.addWidget(self.confirm_password)

        self.show_registration_password = QCheckBox("Show passwords")
        self.show_registration_password.toggled.connect(self._toggle_registration_passwords)
        layout.addWidget(self.show_registration_password)

        self.registration_message = QLabel("")
        self.registration_message.setObjectName("formMessage")
        self.registration_message.setWordWrap(True)
        layout.addWidget(self.registration_message)

        register_button = QPushButton("Create user account")
        register_button.setObjectName("primaryButton")
        register_button.clicked.connect(self._register)
        layout.addWidget(register_button)
        return page

    def _toggle_registration_passwords(self, visible: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        self.registration_password.setEchoMode(mode)
        self.confirm_password.setEchoMode(mode)

    def _login(self) -> None:
        email = self.login_email.text().strip().lower()
        try:
            authenticated, role = self.auth_store.validate_login(
                email, self.login_password.text()
            )
        except (OSError, sqlite3.Error) as exc:
            QMessageBox.critical(self, "Account storage unavailable", str(exc))
            return

        if not authenticated or role != "user":
            self.login_message.setText("Email or password is incorrect.")
            self.login_message.setProperty("status", "error")
            self.login_message.style().unpolish(self.login_message)
            self.login_message.style().polish(self.login_message)
            return

        self.account_email = email
        self.role = role
        self.login_password.clear()
        self.accept()

    def _admin_login(self) -> None:
        email = self.admin_email_input.text().strip().lower()
        try:
            authenticated, role = self.auth_store.validate_login(
                email, self.admin_password_input.text()
            )
        except (OSError, sqlite3.Error) as exc:
            QMessageBox.critical(self, "Account storage unavailable", str(exc))
            return

        if not authenticated or role != "admin":
            self.admin_login_message.setText(
                "Administrator email or password is incorrect."
            )
            self.admin_login_message.setProperty("status", "error")
            self.admin_login_message.style().unpolish(self.admin_login_message)
            self.admin_login_message.style().polish(self.admin_login_message)
            return

        self.account_email = email
        self.role = "admin"
        self.admin_password_input.clear()
        self.accept()

    def _register(self) -> None:
        if self.registration_password.text() != self.confirm_password.text():
            self._set_registration_message("Passwords do not match.", "error")
            return

        try:
            status = self.auth_store.register_user(
                self.registration_email.text(), self.registration_password.text()
            )
        except (OSError, sqlite3.Error) as exc:
            QMessageBox.critical(self, "Account storage unavailable", str(exc))
            return

        messages = {
            "invalid_email": "Enter a valid email address.",
            "reserved_email": "That email is reserved for the administrator.",
            "weak_password": "Choose a password with at least 8 characters.",
            "already_registered": "An account with that email already exists.",
        }
        if status == "registered":
            email = self.registration_email.text().strip().lower()
            self.login_email.setText(email)
            self.login_password.clear()
            self.registration_password.clear()
            self.confirm_password.clear()
            self._set_registration_message(
                "Account created. Sign in with your new account to continue.", "success"
            )
            self.auth_tabs.setCurrentIndex(0)
            return
        self._set_registration_message(messages.get(status, "Could not create the account."), "error")

    def _set_registration_message(self, message: str, status: str) -> None:
        self.registration_message.setText(message)
        self.registration_message.setProperty("status", status)
        self.registration_message.style().unpolish(self.registration_message)
        self.registration_message.style().polish(self.registration_message)


class PasswordResetDialog(QDialog):
    def __init__(self, email: str) -> None:
        super().__init__()
        self.setWindowTitle("Set user password")
        self.setMinimumWidth(400)
        self.new_password: str | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Set a new password for {email}"))
        layout.addWidget(QLabel("New password (at least 8 characters)"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)
        layout.addWidget(QLabel("Confirm new password"))
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.returnPressed.connect(self._submit)
        layout.addWidget(self.confirm_input)

        self.show_password = QCheckBox("Show passwords")
        self.show_password.toggled.connect(self._toggle_passwords)
        layout.addWidget(self.show_password)
        self.message = QLabel("")
        self.message.setObjectName("formMessage")
        layout.addWidget(self.message)

        buttons = QHBoxLayout()
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        save_button = QPushButton("Save new password")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self._submit)
        buttons.addStretch(1)
        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)
        layout.addLayout(buttons)

    def _toggle_passwords(self, visible: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        self.password_input.setEchoMode(mode)
        self.confirm_input.setEchoMode(mode)

    def _submit(self) -> None:
        password = self.password_input.text()
        if len(password) < 8:
            self.message.setText("Password must contain at least 8 characters.")
            self.message.setProperty("status", "error")
            return
        if password != self.confirm_input.text():
            self.message.setText("Passwords do not match.")
            self.message.setProperty("status", "error")
            return
        self.new_password = password
        self.accept()


class BugFinderWindow(QMainWindow):
    def __init__(
        self,
        account_email: str = "Developer",
        history_store: HistoryStore | None = None,
        auth_store: AuthStore | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("AI Bug Finder")
        self.resize(1180, 760)
        self.account_email = account_email
        self.history_store = history_store or HistoryStore()
        self.auth_store = auth_store or AuthStore()
        self.current_file: Path | None = None
        self.analysis_result: dict[str, Any] | None = None

        self.source_editor = QPlainTextEdit()
        self.source_editor.setPlaceholderText("Paste Python code here or open a .py file.")
        self.source_editor.setPlainText(DEFAULT_CODE)
        self.source_editor.setTabStopDistance(32)

        self.findings_table = QTableWidget(0, 3)
        self.findings_table.setHorizontalHeaderLabels(["Severity", "Line", "Finding"])
        self.findings_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.findings_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.findings_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.findings_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.findings_table.itemSelectionChanged.connect(self._show_selected_finding)

        self.finding_details = QPlainTextEdit()
        self.finding_details.setReadOnly(True)
        self.finding_details.setPlaceholderText("Select a finding to see its details and suggested fix.")

        self.fixed_preview = QPlainTextEdit()
        self.fixed_preview.setReadOnly(True)
        self.fixed_preview.setPlaceholderText("Conservative fix suggestions will appear here after analysis.")

        self.summary_label = QLabel("Ready to analyze Python code.")
        self.summary_label.setObjectName("summaryLabel")
        self.file_label = QLabel("No file opened")
        self.file_label.setObjectName("mutedLabel")
        self.runtime_checkbox = QCheckBox("Run optional runtime smoke test")
        self.runtime_checkbox.setToolTip(
            "Executes the submitted code in the analyzer's runtime checker. "
            "Only enable this for code you trust."
        )

        open_button = QPushButton("Open Python file")
        open_button.clicked.connect(self._open_file)
        analyze_button = QPushButton("Analyze code")
        analyze_button.setDefault(True)
        analyze_button.clicked.connect(self._analyze)
        self.save_fix_button = QPushButton("Save corrected code")
        self.save_fix_button.setEnabled(False)
        self.save_fix_button.clicked.connect(self._save_fixed_code)
        self.export_button = QPushButton("Export report")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export_report)
        self.logout_button = QPushButton("Sign out")
        self.logout_button.setObjectName("secondaryButton")
        self.logout_button.clicked.connect(self._sign_out)

        toolbar = QWidget()
        toolbar_layout = QVBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_title = QLabel("AI Bug Finder")
        header_title.setObjectName("workspaceTitle")
        signed_in = QLabel(f"Signed in  |  {self.account_email}")
        signed_in.setObjectName("mutedLabel")
        header_layout.addWidget(header_title)
        header_layout.addStretch(1)
        header_layout.addWidget(signed_in)
        header_layout.addWidget(self.logout_button)
        button_row = QWidget()
        button_layout = QHBoxLayout(button_row)
        button_layout.setContentsMargins(0, 0, 0, 0)
        for widget in (
            open_button,
            analyze_button,
            self.runtime_checkbox,
            self.save_fix_button,
            self.export_button,
        ):
            button_layout.addWidget(widget)
        button_layout.addStretch(1)
        toolbar_layout.addWidget(header)
        toolbar_layout.addWidget(self.file_label)
        toolbar_layout.addWidget(button_row)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Python source"))
        left_layout.addWidget(self.source_editor)
        left_layout.addWidget(QLabel("Conservative fix preview"))
        left_layout.addWidget(self.fixed_preview)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("Findings"))
        right_layout.addWidget(self.findings_table, 2)
        right_layout.addWidget(QLabel("Finding details"))
        right_layout.addWidget(self.finding_details, 1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        analyzer_page = QWidget()
        analyzer_layout = QVBoxLayout(analyzer_page)
        analyzer_layout.addWidget(self.summary_label)
        analyzer_layout.addWidget(splitter, 1)

        history_page = QWidget()
        history_layout = QVBoxLayout(history_page)
        self.history_records: list[dict[str, Any]] = []
        self.history_table = QTableWidget(0, 3)
        self.history_table.setHorizontalHeaderLabels(["File", "Analyzed", "Findings"])
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.itemSelectionChanged.connect(self._show_selected_history)
        self.history_detail = QPlainTextEdit()
        self.history_detail.setReadOnly(True)
        self.history_detail.setPlaceholderText("Select a saved analysis to review its source and findings.")
        history_actions = QHBoxLayout()
        refresh_history = QPushButton("Refresh history")
        refresh_history.setObjectName("secondaryButton")
        refresh_history.clicked.connect(self._refresh_user_history)
        self.load_history_button = QPushButton("Load source into editor")
        self.load_history_button.clicked.connect(self._load_selected_history)
        self.load_history_button.setEnabled(False)
        history_actions.addWidget(refresh_history)
        history_actions.addWidget(self.load_history_button)
        history_actions.addStretch(1)
        history_layout.addWidget(self.history_table, 2)
        history_layout.addWidget(self.history_detail, 2)
        history_layout.addLayout(history_actions)

        self.workspace_tabs = QTabWidget()
        self.workspace_tabs.addTab(analyzer_page, "Analyze code")
        self.workspace_tabs.addTab(history_page, "My history")

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(toolbar)
        layout.addWidget(self.workspace_tabs, 1)
        self.setCentralWidget(central)
        self.source_editor.textChanged.connect(self._clear_analysis)
        self._refresh_user_history()

    def _open_file(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Python file",
            str(self.current_file.parent) if self.current_file else "",
            "Python files (*.py);;All files (*)",
        )
        if not file_name:
            return

        path = Path(file_name)
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            QMessageBox.critical(self, "Could not open file", str(exc))
            return

        self.current_file = path
        self.source_editor.setPlainText(source)
        self.file_label.setText(str(path))
        self._clear_analysis()

    def _analyze(self) -> None:
        source = self.source_editor.toPlainText()
        result = detect_bugs(source, run_code=self.runtime_checkbox.isChecked())
        self.analysis_result = result
        summary = result["summary"]
        self.summary_label.setText(
            f"Findings: {summary['total']}    Errors: {summary['errors']}    "
            f"Warnings: {summary['warnings']}"
        )

        issues = result.get("issues", [])
        self.findings_table.setRowCount(len(issues))
        for row, issue in enumerate(issues):
            severity = str(issue.get("severity", "info")).capitalize()
            line = issue.get("line")
            values = (severity, str(line) if line else "-", str(issue.get("title", "Code issue")))
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, issue)
                self.findings_table.setItem(row, column, item)

        fixed_code = result.get("fixed_code")
        self.fixed_preview.setPlainText(
            fixed_code
            if fixed_code is not None
            else (
                "No safe automatic fix is available for these findings. "
                "See Finding details for guidance; some fixes need your intended values."
            )
        )
        self.save_fix_button.setEnabled(fixed_code is not None)
        self.export_button.setEnabled(True)
        self.finding_details.clear()
        if issues:
            self.findings_table.selectRow(0)
        else:
            self.finding_details.setPlainText("No issues detected.")
        try:
            self.history_store.add(
                self.account_email,
                self.current_file.name if self.current_file else "pasted-code",
                source,
                result,
            )
        except (OSError, RuntimeError, sqlite3.Error) as exc:
            QMessageBox.critical(self, "Could not save analysis history", str(exc))
        else:
            self._refresh_user_history()

    def _refresh_user_history(self) -> None:
        try:
            self.history_records = list(reversed(self.history_store.list_for_user(self.account_email)))
        except (OSError, RuntimeError, sqlite3.Error) as exc:
            QMessageBox.critical(self, "Could not load analysis history", str(exc))
            return

        self.history_table.setRowCount(len(self.history_records))
        for row, record in enumerate(self.history_records):
            values = (
                record["filename"],
                record["created_at"].replace("T", " ")[:19],
                str(record["result"].get("summary", {}).get("total", 0)),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, row)
                self.history_table.setItem(row, column, item)
        self.history_detail.clear()
        self.load_history_button.setEnabled(False)

    def _selected_history_record(self) -> dict[str, Any] | None:
        selected = self.history_table.selectedItems()
        if not selected:
            return None
        row_index = selected[0].data(Qt.ItemDataRole.UserRole)
        if not isinstance(row_index, int) or row_index >= len(self.history_records):
            return None
        return self.history_records[row_index]

    def _show_selected_history(self) -> None:
        record = self._selected_history_record()
        if record is None:
            return
        self.load_history_button.setEnabled(True)
        result = record["result"]
        lines = [
            f"File: {record['filename']}",
            f"Analyzed: {record['created_at']}",
            "",
            "Source:",
            record["source"],
            "",
            "Findings:",
        ]
        lines.extend(
            f"- {issue.get('severity', 'finding')}: {issue.get('title', 'Issue')} "
            f"(line {issue.get('line', '-')}) - {issue.get('message', '')}"
            for issue in result.get("issues", [])
        )
        if not result.get("issues"):
            lines.append("No findings.")
        self.history_detail.setPlainText("\n".join(lines))

    def _load_selected_history(self) -> None:
        record = self._selected_history_record()
        if record is None:
            return
        self.current_file = None
        self.source_editor.setPlainText(record["source"])
        self.file_label.setText(f"Loaded from history: {record['filename']}")
        self.workspace_tabs.setCurrentIndex(0)

    def _show_selected_finding(self) -> None:
        selected_items = self.findings_table.selectedItems()
        if not selected_items:
            return
        issue = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if not isinstance(issue, dict):
            return

        parts = [
            str(issue.get("message", "")),
            "",
            f"Suggested fix: {issue.get('solution') or issue.get('suggestion') or 'No fix suggestion provided.'}",
        ]
        if issue.get("code_solution"):
            parts.extend(["", "Example:", str(issue["code_solution"])])
        self.finding_details.setPlainText("\n".join(parts))

    def _save_fixed_code(self) -> None:
        if not self.analysis_result or self.analysis_result.get("fixed_code") is None:
            return
        default_name = (
            f"{self.current_file.stem}-fixed.py" if self.current_file else "corrected_code.py"
        )
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save corrected code", default_name, "Python files (*.py)"
        )
        if not file_name:
            return
        path = Path(file_name)
        if path.suffix.lower() != ".py":
            path = path.with_suffix(".py")
        try:
            path.write_text(self.analysis_result["fixed_code"], encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Could not save corrected code", str(exc))
            return
        QMessageBox.information(self, "Saved", f"Corrected code saved to:\n{path}")

    def _export_report(self) -> None:
        if not self.analysis_result:
            return
        file_name, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export analysis report",
            "bug-report.json",
            "JSON report (*.json);;Markdown report (*.md);;PDF report (*.pdf)",
        )
        if not file_name:
            return

        extension_by_filter = {
            "JSON report (*.json)": ".json",
            "Markdown report (*.md)": ".md",
            "PDF report (*.pdf)": ".pdf",
        }
        path = Path(file_name)
        supported_suffixes = set(extension_by_filter.values())
        expected_suffix = (
            path.suffix.lower()
            if path.suffix.lower() in supported_suffixes
            else extension_by_filter.get(selected_filter)
        )
        if expected_suffix is None:
            QMessageBox.warning(self, "Unsupported report format", "Select JSON, Markdown, or PDF.")
            return
        if path.suffix.lower() != expected_suffix:
            path = path.with_suffix(expected_suffix)

        source = self.source_editor.toPlainText()
        if expected_suffix == ".json":
            content: str | bytes = create_json_report(source, self.analysis_result)
        elif expected_suffix == ".md":
            content = report_as_markdown(source, self.analysis_result)
        else:
            content = create_pdf_report(source, self.analysis_result)

        try:
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_text(content, encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Could not export report", str(exc))
            return
        QMessageBox.information(self, "Report exported", f"Report saved to:\n{path}")

    def _clear_analysis(self) -> None:
        self.analysis_result = None
        self.findings_table.setRowCount(0)
        self.finding_details.clear()
        self.fixed_preview.clear()
        self.summary_label.setText("Ready to analyze Python code.")
        self.save_fix_button.setEnabled(False)
        self.export_button.setEnabled(False)

    def _sign_out(self) -> None:
        self.hide()
        _show_auth_window(self.auth_store, self, self.history_store)


class AdminWindow(QMainWindow):
    def __init__(
        self,
        account_email: str,
        auth_store: AuthStore,
        history_store: HistoryStore,
    ) -> None:
        super().__init__()
        self.account_email = account_email
        self.auth_store = auth_store
        self.history_store = history_store
        self.records: list[dict[str, Any]] = []
        self.setWindowTitle("AI Bug Finder | Administrator")
        self.resize(1000, 700)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        header = QHBoxLayout()
        heading = QVBoxLayout()
        title = QLabel("Administrator console")
        title.setObjectName("workspaceTitle")
        subtitle = QLabel(
            f"Account oversight and saved analysis history  |  {self.account_email}"
        )
        subtitle.setObjectName("mutedLabel")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        header.addLayout(heading)
        header.addStretch(1)
        refresh_button = QPushButton("Refresh data")
        refresh_button.setObjectName("secondaryButton")
        refresh_button.clicked.connect(self._refresh_data)
        header.addWidget(refresh_button)
        logout_button = QPushButton("Sign out")
        logout_button.setObjectName("primaryButton")
        logout_button.clicked.connect(self._sign_out)
        header.addWidget(logout_button)
        layout.addLayout(header)

        self.admin_tabs = QTabWidget()
        self.users_table = QTableWidget(0, 2)
        self.users_table.setHorizontalHeaderLabels(["Email", "Registered"])
        self._configure_table(self.users_table)
        self.users_table.itemSelectionChanged.connect(self._update_user_actions)
        users_page = QWidget()
        users_layout = QVBoxLayout(users_page)
        users_layout.addWidget(QLabel("Select a user to set a new password. Existing passwords are never shown."))
        users_layout.addWidget(self.users_table, 1)
        user_actions = QHBoxLayout()
        self.reset_password_button = QPushButton("Set / reset password")
        self.reset_password_button.setObjectName("primaryButton")
        self.reset_password_button.setEnabled(False)
        self.reset_password_button.clicked.connect(self._reset_selected_user_password)
        user_actions.addWidget(self.reset_password_button)
        user_actions.addStretch(1)
        users_layout.addLayout(user_actions)
        self.admin_tabs.addTab(users_page, "Registered users")

        history_page = QWidget()
        history_layout = QVBoxLayout(history_page)
        self.history_table = QTableWidget(0, 4)
        self.history_table.setHorizontalHeaderLabels(
            ["Account", "File", "Analyzed", "Findings"]
        )
        self._configure_table(self.history_table)
        self.history_table.itemSelectionChanged.connect(self._show_history_record)
        self.history_details = QPlainTextEdit()
        self.history_details.setReadOnly(True)
        self.history_details.setPlaceholderText("Select an analysis to view its source and findings.")
        history_layout.addWidget(self.history_table, 3)
        history_layout.addWidget(self.history_details, 2)
        self.admin_tabs.addTab(history_page, "Analysis history")
        layout.addWidget(self.admin_tabs)

        self.setCentralWidget(central)
        self._refresh_data()

    @staticmethod
    def _configure_table(table: QTableWidget) -> None:
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def _refresh_data(self) -> None:
        try:
            users = self.auth_store.list_users()
            self.records = list(reversed(self.history_store.list_all()))
        except (OSError, RuntimeError, sqlite3.Error) as exc:
            QMessageBox.critical(self, "Could not load administrator data", str(exc))
            return

        self.users_table.setRowCount(len(users))
        for row, user in enumerate(users):
            values = (user["email"], user["created_at"].replace("T", " ")[:19])
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, user["email"])
                self.users_table.setItem(row, column, item)
        self.reset_password_button.setEnabled(False)

        self.history_table.setRowCount(len(self.records))
        for row, record in enumerate(self.records):
            values = (
                record["user"],
                record["filename"],
                record["created_at"].replace("T", " ")[:19],
                str(record["result"].get("summary", {}).get("total", 0)),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, row)
                self.history_table.setItem(row, column, item)
        self.history_details.clear()

    def _selected_user_email(self) -> str | None:
        selected = self.users_table.selectedItems()
        if not selected:
            return None
        email = selected[0].data(Qt.ItemDataRole.UserRole)
        return email if isinstance(email, str) else None

    def _update_user_actions(self) -> None:
        self.reset_password_button.setEnabled(self._selected_user_email() is not None)

    def _reset_selected_user_password(self) -> None:
        email = self._selected_user_email()
        if email is None:
            return
        dialog = PasswordResetDialog(email)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.new_password is None:
            return
        try:
            status = self.auth_store.reset_user_password(email, dialog.new_password)
        except (OSError, sqlite3.Error) as exc:
            QMessageBox.critical(self, "Could not update password", str(exc))
            return
        if status == "updated":
            QMessageBox.information(
                self,
                "Password updated",
                f"A new password has been set for {email}. The password itself is not saved or displayed.",
            )
        elif status == "weak_password":
            QMessageBox.warning(self, "Password too short", "Use at least 8 characters.")
        else:
            QMessageBox.warning(self, "User not found", "Refresh the user list and try again.")

    def _show_history_record(self) -> None:
        selected = self.history_table.selectedItems()
        if not selected:
            return
        row_index = selected[0].data(Qt.ItemDataRole.UserRole)
        if not isinstance(row_index, int) or row_index >= len(self.records):
            return
        record = self.records[row_index]
        result = record["result"]
        findings = result.get("issues", [])
        lines = [
            f"Account: {record['user']}",
            f"File: {record['filename']}",
            f"Created: {record['created_at']}",
            "",
            "Source:",
            record["source"],
            "",
            "Findings:",
        ]
        lines.extend(
            f"- {issue.get('severity', 'finding')}: {issue.get('title', 'Issue')} "
            f"(line {issue.get('line', '-')}) - {issue.get('message', '')}"
            for issue in findings
        )
        if not findings:
            lines.append("No findings.")
        self.history_details.setPlainText("\n".join(lines))

    def _sign_out(self) -> None:
        self.hide()
        _show_auth_window(self.auth_store, self, self.history_store)


_active_window: QMainWindow | None = None


def _create_desktop_stores() -> tuple[AuthStore, HistoryStore]:
    if not getattr(sys, "frozen", False):
        return AuthStore(), HistoryStore()

    local_app_data = Path(
        os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
    )
    data_directory = local_app_data / "AI Bug Finder"
    data_directory.mkdir(parents=True, exist_ok=True)
    return (
        AuthStore(data_directory / "users.db"),
        HistoryStore(data_directory / "history.db"),
    )


def _show_auth_window(
    auth_store: AuthStore,
    previous_window: QMainWindow | None = None,
    history_store: HistoryStore | None = None,
) -> bool:
    global _active_window
    dialog = AuthDialog(auth_store)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        if previous_window is not None:
            previous_window.show()
        return False
    if dialog.account_email is None or dialog.role is None:
        if previous_window is not None:
            previous_window.show()
        return False

    try:
        if history_store is None:
            history_store = HistoryStore()
    except (OSError, RuntimeError, sqlite3.Error) as exc:
        QMessageBox.critical(None, "Could not open analysis history", str(exc))
        if previous_window is not None:
            previous_window.show()
        return False
    if dialog.role == "admin":
        window: QMainWindow = AdminWindow(
            dialog.account_email, auth_store, history_store
        )
    else:
        window = BugFinderWindow(dialog.account_email, history_store, auth_store)
    window.show()
    _active_window = window
    if previous_window is not None:
        previous_window.close()
    return True


APP_STYLESHEET = """
QWidget {
    color: #172b4d;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QMainWindow, QDialog { background: #f2f5fa; }
QWidget#authCard, QWidget#centralwidget {
    background: #ffffff;
}
QDialog QWidget#authCard {
    border: 1px solid #e4eaf2;
    border-radius: 22px;
}
QLabel#brandLabel {
    color: #087e8b;
    font-size: 11pt;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#eyebrowLabel {
    color: #8492a6;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 1.3px;
}
QLabel#authTitle {
    color: #142b4a;
    font-size: 25pt;
    font-weight: 700;
}
QLabel#workspaceTitle {
    color: #142b4a;
    font-size: 20pt;
    font-weight: 700;
}
QLabel#mutedLabel, QLabel#helperLabel {
    color: #718096;
}
QLabel#helperLabel { font-size: 9pt; }
QLabel#summaryLabel {
    padding: 10px 14px;
    color: #11636a;
    background: #e3f5f3;
    border: 1px solid #c6e9e4;
    border-radius: 9px;
    font-weight: 600;
}
QLabel#formMessage[status="error"] { color: #b42318; }
QLabel#formMessage[status="success"] { color: #16804a; }
QLineEdit, QPlainTextEdit, QTableWidget {
    background: #ffffff;
    border: 1px solid #d8e1ec;
    border-radius: 9px;
    padding: 9px;
    selection-background-color: #b9e5e5;
}
QLineEdit:focus, QPlainTextEdit:focus, QTableWidget:focus {
    border: 1px solid #13838a;
}
QPlainTextEdit { font-family: "Cascadia Code", "Consolas"; }
QTableWidget { gridline-color: #edf1f6; }
QHeaderView::section {
    color: #52647b;
    background: #f3f6fa;
    border: none;
    border-bottom: 1px solid #dce4ee;
    padding: 10px;
    font-weight: 600;
}
QPushButton {
    color: #33445d;
    background: #ffffff;
    border: 1px solid #d6e0eb;
    border-radius: 9px;
    padding: 9px 14px;
    font-weight: 600;
}
QPushButton:hover { background: #f2f8fa; border-color: #92c8ca; }
QPushButton:disabled { color: #9aa7b7; background: #edf1f5; }
QPushButton#primaryButton {
    color: #ffffff;
    background: #087e8b;
    border: 1px solid #087e8b;
}
QPushButton#primaryButton:hover { background: #066a75; }
QPushButton#secondaryButton { color: #12636b; background: #e8f4f4; }
QPushButton#secondaryButton:hover { background: #d7ecec; }
QTabWidget::pane {
    border: 1px solid #e0e7ef;
    border-radius: 10px;
    background: #ffffff;
    top: -1px;
}
QTabBar::tab {
    color: #687a91;
    background: transparent;
    padding: 10px 16px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    color: #087e8b;
    border-bottom: 2px solid #087e8b;
    font-weight: 700;
}
QCheckBox { color: #52647b; spacing: 7px; }
QSplitter::handle { background: #e0e7ef; width: 5px; }
"""


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)
    app.setApplicationName("AI Bug Finder")
    auth_store, history_store = _create_desktop_stores()
    if not _show_auth_window(auth_store, history_store=history_store):
        return 0
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
