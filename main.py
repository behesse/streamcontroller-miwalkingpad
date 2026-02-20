import os

import gi
from gi.repository import Gtk

# Import StreamController modules
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.DeckManagement.InputIdentifier import Input
from src.backend.DeckManagement.ImageHelpers import image2pixbuf

# Import actions
from .actions.SpeedDown.SpeedDown import SpeedDown
from .actions.SpeedUp.SpeedUp import SpeedUp
from .actions.ToggleStartStop.ToggleStartStop import ToggleStartStop

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw


class MiWalkingPadPlugin(PluginBase):
    KEY_ONLY_SUPPORT = {
        Input.Key: ActionInputSupport.SUPPORTED,
        Input.Dial: ActionInputSupport.UNSUPPORTED,
        Input.Touchscreen: ActionInputSupport.UNSUPPORTED,
    }

    def __init__(self):
        super().__init__()

        self._last_saved_ip = ""
        self._last_saved_token = ""

        self._add_icons()

        backend_path = os.path.join(self.PATH, "backend", "backend.py")
        backend_venv = os.path.join(self.PATH, "backend", ".venv")
        self.launch_backend(
            backend_path=backend_path,
            venv_path=backend_venv if os.path.isdir(backend_venv) else None,
            open_in_terminal=False,
        )


        self.toggle_start_stop_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleStartStop,
            action_id="com_behesse_miwalkingpad::ToggleStartStop",
            action_name="Start / Stop",
            action_support=self.KEY_ONLY_SUPPORT,
        )
        self.add_action_holder(self.toggle_start_stop_action_holder)

        self.speed_up_action_holder = ActionHolder(
            plugin_base=self,
            action_base=SpeedUp,
            action_id="com_behesse_miwalkingpad::SpeedUp",
            action_name="Speed +0.5",
            action_support=self.KEY_ONLY_SUPPORT,
        )
        self.add_action_holder(self.speed_up_action_holder)

        self.speed_down_action_holder = ActionHolder(
            plugin_base=self,
            action_base=SpeedDown,
            action_id="com_behesse_miwalkingpad::SpeedDown",
            action_name="Speed -0.5",
            action_support=self.KEY_ONLY_SUPPORT,
        )
        self.add_action_holder(self.speed_down_action_holder)

        self.register(
            plugin_name="Mi WalkingPad",
            github_repo="https://github.com/behesse/streamcontroller-miwalkingpad",
            plugin_version="0.1.0",
            app_version="1.5.0-beta.6",
        )

        self._sync_backend_config()

    def get_selector_icon(self) -> Gtk.Widget:
        _, rendered = self.asset_manager.icons.get_asset_values("main")
        return Gtk.Image.new_from_pixbuf(image2pixbuf(rendered))

    def _add_icons(self) -> None:
        self.add_icon("main", self.get_asset_path("treadmill.svg"))
        self.add_icon("offline", self.get_asset_path("treadmill-offline.svg"))
        self.add_icon("pause", self.get_asset_path("pause.svg"))
        self.add_icon("speed-up", self.get_asset_path("up.svg"))
        self.add_icon("speed-down", self.get_asset_path("down.svg"))

    def _sync_backend_config(self) -> None:
        settings = self.get_settings()
        ip = str(settings.get("walkingpad_ip", "")).strip()
        token = str(settings.get("walkingpad_token", "")).strip()

        try:
            if self.backend is not None:
                self.backend.configure(ip=ip, token=token)
        except Exception:
            # Backend may still be starting.
            pass

    def get_settings_area(self):
        settings = self.get_settings()

        group = Adw.PreferencesGroup(title="WalkingPad Connection")

        self.ip_row = Adw.EntryRow(title="WalkingPad IP")
        self.ip_row.set_text(str(settings.get("walkingpad_ip", "")))

        self.token_row = Adw.EntryRow(title="WalkingPad token")
        self.token_row.set_text(str(settings.get("walkingpad_token", "")))

        group.add(self.ip_row)
        group.add(self.token_row)

        self.ip_row.connect("changed", self._on_ip_changed)
        self.token_row.connect("changed", self._on_token_changed)
        self.ip_row.connect("apply", self._on_ip_changed)
        self.token_row.connect("apply", self._on_token_changed)
        self.ip_row.connect("notify::has-focus", self._on_ip_focus_changed)
        self.token_row.connect("notify::has-focus", self._on_token_focus_changed)

        return group

    def _save_plugin_settings(self) -> None:
        ip = self.ip_row.get_text().strip()
        token = self.token_row.get_text().strip()

        if ip == self._last_saved_ip and token == self._last_saved_token:
            return

        settings = self.get_settings()
        settings["walkingpad_ip"] = ip
        settings["walkingpad_token"] = token
        self.set_settings(settings)

        self._last_saved_ip = ip
        self._last_saved_token = token
        self._sync_backend_config()

    def _on_ip_changed(self, *_args) -> None:
        self._save_plugin_settings()

    def _on_token_changed(self, *_args) -> None:
        self._save_plugin_settings()

    def _on_ip_focus_changed(self, row, _param) -> None:
        if not row.get_has_focus():
            self._save_plugin_settings()

    def _on_token_focus_changed(self, row, _param) -> None:
        if not row.get_has_focus():
            self._save_plugin_settings()
