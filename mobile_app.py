from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from auth_manager import AuthStore
from database import HistoryStore
from engine import detect_bugs


BACKGROUND = (0.95, 0.97, 0.99, 1)
NAVY = (0.08, 0.16, 0.27, 1)
TEAL = (0.03, 0.48, 0.53, 1)
WHITE = (1, 1, 1, 1)
MUTED = (0.38, 0.45, 0.54, 1)


def styled_label(
    text: str,
    *,
    size: str = "16sp",
    color: tuple[float, float, float, float] = NAVY,
    height: float | None = None,
) -> Label:
    label = Label(
        text=text,
        size_hint_y=None,
        height=dp(height) if height is not None else dp(32),
        color=color,
        font_size=size,
        halign="left",
        valign="middle",
    )
    label.bind(size=lambda widget, value: setattr(widget, "text_size", (value[0], None)))
    label.bind(
        texture_size=lambda widget, value: setattr(
            widget, "height", max(dp(height or 32), value[1] + dp(8))
        )
    )
    return label


def make_button(text: str, callback: Any, *, primary: bool = False) -> Button:
    button = Button(
        text=text,
        size_hint_y=None,
        height=dp(48),
        background_normal="",
        background_color=TEAL if primary else (0.89, 0.93, 0.96, 1),
        color=WHITE if primary else NAVY,
        font_size="15sp",
    )
    button.bind(on_release=callback)
    return button


def make_input(hint: str, *, password: bool = False, multiline: bool = False) -> TextInput:
    return TextInput(
        hint_text=hint,
        password=password,
        multiline=multiline,
        size_hint_y=None,
        height=dp(52) if not multiline else dp(250),
        padding=(dp(12), dp(12)),
        background_normal="",
        background_active="",
        background_color=WHITE,
        foreground_color=NAVY,
        cursor_color=TEAL,
        hint_text_color=MUTED,
        font_size="16sp",
    )


class MobileAuthScreen(Screen):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(name="auth", **kwargs)
        root = BoxLayout(
            orientation="vertical",
            padding=(dp(24), dp(28)),
            spacing=dp(12),
        )
        root.add_widget(styled_label("AI BUG FINDER", size="13sp", color=TEAL, height=26))
        root.add_widget(
            styled_label(
                "Find bugs before they reach production.",
                size="27sp",
                height=76,
            )
        )
        root.add_widget(
            styled_label(
                "Sign in or create an account to analyze Python code on this device.",
                size="15sp",
                color=MUTED,
                height=54,
            )
        )

        self.email_input = make_input("Email address")
        self.password_input = make_input("Password", password=True)
        self.register_email = make_input("Email address for new account")
        self.register_password = make_input("Password (at least 8 characters)", password=True)
        self.register_confirm = make_input("Confirm password", password=True)
        for widget in (self.email_input, self.password_input):
            root.add_widget(widget)

        self.message = styled_label("", size="14sp", color=TEAL, height=48)
        root.add_widget(self.message)
        root.add_widget(make_button("Sign in as user", self._login_user, primary=True))
        root.add_widget(make_button("Admin login", self._login_admin))
        root.add_widget(make_button("Show registration", self._toggle_registration))

        self.registration_panel = BoxLayout(
            orientation="vertical",
            spacing=dp(9),
            size_hint_y=None,
            height=0,
            opacity=0,
            disabled=True,
        )
        self.registration_panel.add_widget(styled_label("Create a user account", size="18sp", height=34))
        self.registration_panel.add_widget(self.register_email)
        self.registration_panel.add_widget(self.register_password)
        self.registration_panel.add_widget(self.register_confirm)
        self.registration_panel.add_widget(
            make_button("Create account", self._register, primary=True)
        )

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))
        for child in list(root.children)[::-1]:
            root.remove_widget(child)
            content.add_widget(child)
        content.add_widget(self.registration_panel)

        scroller = ScrollView(do_scroll_x=False)
        scroller.add_widget(content)
        root.add_widget(scroller)
        self.add_widget(root)

    def on_pre_enter(self, *args: Any) -> None:
        self.email_input.text = ""
        self.password_input.text = ""

    def _toggle_registration(self, *_: Any) -> None:
        panel = self.registration_panel
        if panel.height:
            panel.height = 0
            panel.opacity = 0
            panel.disabled = True
        else:
            panel.height = dp(370)
            panel.opacity = 1
            panel.disabled = False
            self.message.text = ""

    def _login_user(self, *_: Any) -> None:
        self._login(expected_role="user")

    def _login_admin(self, *_: Any) -> None:
        self._login(expected_role="admin")

    def _login(self, expected_role: str) -> None:
        app = App.get_running_app()
        email = self.email_input.text.strip().lower()
        try:
            valid, role = app.auth_store.validate_login(email, self.password_input.text)
        except (OSError, sqlite3.Error) as exc:
            self.message.text = f"Account storage error: {exc}"
            return
        if not valid or role != expected_role:
            self.message.text = (
                "Email or password is incorrect."
                if expected_role == "user"
                else "Administrator email or password is incorrect."
            )
            return
        app.open_workspace(email, role)

    def _register(self, *_: Any) -> None:
        app = App.get_running_app()
        if self.register_password.text != self.register_confirm.text:
            self.message.text = "The passwords do not match."
            return
        try:
            status = app.auth_store.register_user(
                self.register_email.text, self.register_password.text
            )
        except (OSError, sqlite3.Error) as exc:
            self.message.text = f"Account storage error: {exc}"
            return
        messages = {
            "registered": "Account created. Sign in with your email and password.",
            "invalid_email": "Enter a valid email address.",
            "reserved_email": "That email is reserved for the administrator.",
            "weak_password": "Choose a password with at least 8 characters.",
            "already_registered": "An account with that email already exists.",
        }
        self.message.text = messages.get(status, "Could not create the account.")
        if status == "registered":
            self.email_input.text = self.register_email.text.strip().lower()
            self.register_password.text = ""
            self.register_confirm.text = ""


class UserScreen(Screen):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(name="user", **kwargs)
        self.account_email = ""
        self.analysis_result: dict[str, Any] | None = None
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        header = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        self.account_label = styled_label("User workspace", size="16sp")
        header.add_widget(self.account_label)
        header.add_widget(make_button("Sign out", self._sign_out))
        root.add_widget(header)
        root.add_widget(make_button("Open saved history", self._open_history))
        self.source_input = make_input("Paste Python code here", multiline=True)
        root.add_widget(self.source_input)
        root.add_widget(
            make_button("Analyze code", self._analyze, primary=True)
        )

        result_scroller = ScrollView(do_scroll_x=False)
        self.result_content = BoxLayout(
            orientation="vertical",
            spacing=dp(9),
            size_hint_y=None,
            padding=(dp(4), dp(8)),
        )
        self.result_content.bind(minimum_height=self.result_content.setter("height"))
        result_scroller.add_widget(self.result_content)
        root.add_widget(result_scroller)
        self.add_widget(root)

    def set_account(self, email: str) -> None:
        self.account_email = email
        self.account_label.text = f"Signed in: {email}"
        self.source_input.text = ""
        self.result_content.clear_widgets()
        self.analysis_result = None

    def _analyze(self, *_: Any) -> None:
        app = App.get_running_app()
        source = self.source_input.text
        self.analysis_result = detect_bugs(source, run_code=False)
        result = self.analysis_result
        summary = result["summary"]
        self.result_content.clear_widgets()
        self.result_content.add_widget(
            styled_label(
                f"{summary['total']} findings  |  {summary['errors']} errors  |  "
                f"{summary['warnings']} warnings",
                size="17sp",
                height=42,
            )
        )
        fixed_code = result.get("fixed_code")
        self.result_content.add_widget(
            styled_label(
                "Conservative fix preview" if fixed_code else "Fix guidance",
                size="18sp",
                height=38,
            )
        )
        self.result_content.add_widget(
            styled_label(
                fixed_code
                if fixed_code
                else "No safe automatic fix is available for these findings. "
                "Review the guidance below.",
                size="14sp",
                color=MUTED,
            )
        )
        for issue in result.get("issues", []):
            title = f"{issue.get('severity', 'finding').upper()} · {issue.get('title', 'Issue')}"
            line = issue.get("line")
            if line:
                title += f" (line {line})"
            self.result_content.add_widget(styled_label(title, size="15sp", height=36))
            self.result_content.add_widget(
                styled_label(
                    f"{issue.get('message', '')}\nSuggested fix: "
                    f"{issue.get('solution') or issue.get('suggestion') or 'Review this code.'}",
                    size="13sp",
                    color=MUTED,
                )
            )
        try:
            app.history_store.add(
                self.account_email,
                "mobile-pasted-code",
                source,
                result,
            )
        except (OSError, RuntimeError, sqlite3.Error) as exc:
            self.result_content.add_widget(
                styled_label(f"Could not save analysis history: {exc}", color=(0.7, 0.1, 0.1, 1))
            )

    def _open_history(self, *_: Any) -> None:
        App.get_running_app().open_user_history(self.account_email)

    def _sign_out(self, *_: Any) -> None:
        App.get_running_app().sign_out()


class HistoryScreen(Screen):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(name="history", **kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        header = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        header.add_widget(styled_label("My analysis history", size="20sp"))
        header.add_widget(make_button("Back", self._back))
        root.add_widget(header)
        scroller = ScrollView(do_scroll_x=False)
        self.records_content = BoxLayout(
            orientation="vertical", spacing=dp(10), size_hint_y=None
        )
        self.records_content.bind(minimum_height=self.records_content.setter("height"))
        scroller.add_widget(self.records_content)
        root.add_widget(scroller)
        self.add_widget(root)

    def load_records(self, email: str) -> None:
        self.records_content.clear_widgets()
        try:
            records = list(reversed(App.get_running_app().history_store.list_for_user(email)))
        except (OSError, RuntimeError, sqlite3.Error) as exc:
            self.records_content.add_widget(styled_label(f"History error: {exc}"))
            return
        if not records:
            self.records_content.add_widget(styled_label("No analyses saved yet."))
            return
        for record in records:
            summary = record["result"].get("summary", {})
            self.records_content.add_widget(
                styled_label(
                    f"{record['filename']}  |  "
                    f"{record['created_at'].replace('T', ' ')[:16]}",
                    size="15sp",
                    height=38,
                )
            )
            self.records_content.add_widget(
                styled_label(
                    f"{summary.get('total', 0)} findings\n{record['source']}",
                    size="13sp",
                    color=MUTED,
                )
            )

    def _back(self, *_: Any) -> None:
        App.get_running_app().screen_manager.current = "user"


class AdminScreen(Screen):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(name="admin", **kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        header = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        header.add_widget(styled_label("Administrator", size="20sp"))
        header.add_widget(make_button("Sign out", self._sign_out))
        root.add_widget(header)
        scroller = ScrollView(do_scroll_x=False)
        self.admin_content = BoxLayout(
            orientation="vertical", spacing=dp(8), size_hint_y=None
        )
        self.admin_content.bind(minimum_height=self.admin_content.setter("height"))
        scroller.add_widget(self.admin_content)
        root.add_widget(scroller)
        root.add_widget(make_button("Refresh", self.refresh, primary=True))
        self.add_widget(root)

    def refresh(self, *_: Any) -> None:
        app = App.get_running_app()
        self.admin_content.clear_widgets()
        self.admin_content.add_widget(styled_label("Registered users", size="18sp", height=38))
        try:
            users = app.auth_store.list_users()
            records = list(reversed(app.history_store.list_all()))
        except (OSError, RuntimeError, sqlite3.Error) as exc:
            self.admin_content.add_widget(styled_label(f"Could not load admin data: {exc}"))
            return

        if not users:
            self.admin_content.add_widget(styled_label("No registered users."))
        for user in users:
            email = user["email"]
            self.admin_content.add_widget(
                styled_label(
                    f"{email}  ·  {user['created_at'][:10]}",
                    size="14sp",
                    height=38,
                )
            )
            password = make_input(f"New password for {email}", password=True)
            confirm = make_input("Confirm new password", password=True)
            self.admin_content.add_widget(password)
            self.admin_content.add_widget(confirm)
            message = styled_label("", size="13sp", height=34)
            self.admin_content.add_widget(message)

            def reset_password(
                _button: Button,
                user_email: str = email,
                password_input: TextInput = password,
                confirm_input: TextInput = confirm,
                message_label: Label = message,
            ) -> None:
                if len(password_input.text) < 8:
                    message_label.text = "Use at least 8 characters."
                    return
                if password_input.text != confirm_input.text:
                    message_label.text = "Passwords do not match."
                    return
                try:
                    status = app.auth_store.reset_user_password(
                        user_email, password_input.text
                    )
                except (OSError, sqlite3.Error) as exc:
                    message_label.text = f"Could not update password: {exc}"
                    return
                message_label.text = (
                    "Password updated; it is stored as a salted hash."
                    if status == "updated"
                    else "Could not update password."
                )
                password_input.text = ""
                confirm_input.text = ""

            self.admin_content.add_widget(
                make_button("Set new password", reset_password)
            )

        self.admin_content.add_widget(styled_label("Recent analysis history", size="18sp", height=42))
        if not records:
            self.admin_content.add_widget(styled_label("No saved analyses."))
        for record in records:
            summary = record["result"].get("summary", {})
            self.admin_content.add_widget(
                styled_label(
                    f"{record['user']}  ·  {record['filename']}  ·  "
                    f"{summary.get('total', 0)} findings",
                    size="14sp",
                    height=38,
                )
            )

    def _sign_out(self, *_: Any) -> None:
        App.get_running_app().sign_out()


class BugFinderMobileApp(App):
    title = "AI Bug Finder"

    def build(self) -> ScreenManager:
        Window.clearcolor = BACKGROUND
        data_directory = Path(self.user_data_dir)
        data_directory.mkdir(parents=True, exist_ok=True)
        self.auth_store = AuthStore(data_directory / "users.db")
        self.history_store = HistoryStore(data_directory / "history.db")

        self.screen_manager = ScreenManager()
        self.screen_manager.add_widget(MobileAuthScreen())
        self.screen_manager.add_widget(UserScreen())
        self.screen_manager.add_widget(HistoryScreen())
        self.screen_manager.add_widget(AdminScreen())
        return self.screen_manager

    def open_workspace(self, email: str, role: str) -> None:
        if role == "admin":
            self.screen_manager.current = "admin"
            self.screen_manager.get_screen("admin").refresh()
        else:
            user_screen = self.screen_manager.get_screen("user")
            user_screen.set_account(email)
            self.screen_manager.current = "user"

    def open_user_history(self, email: str) -> None:
        history_screen = self.screen_manager.get_screen("history")
        history_screen.load_records(email)
        self.screen_manager.current = "history"

    def sign_out(self) -> None:
        self.screen_manager.current = "auth"


if __name__ == "__main__":
    BugFinderMobileApp().run()
