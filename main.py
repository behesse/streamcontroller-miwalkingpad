import os

import gi

# Import StreamController modules
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.DeckManagement.InputIdentifier import Input

# Import actions
from .actions.SpeedDown.SpeedDown import SpeedDown
from .actions.SpeedUp.SpeedUp import SpeedUp
from .actions.ToggleStartStop.ToggleStartStop import ToggleStartStop

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw


class MiWalkingPadPlugin(PluginBase):
    def __init__(self):
        super().__init__()

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
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED,
            },
        )
        self.add_action_holder(self.toggle_start_stop_action_holder)

        self.speed_up_action_holder = ActionHolder(
            plugin_base=self,
            action_base=SpeedUp,
            action_id="com_behesse_miwalkingpad::SpeedUp",
            action_name="Speed +0.5",
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED,
            },
        )
        self.add_action_holder(self.speed_up_action_holder)

        self.speed_down_action_holder = ActionHolder(
            plugin_base=self,
            action_base=SpeedDown,
            action_id="com_behesse_miwalkingpad::SpeedDown",
            action_name="Speed -0.5",
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED,
            },
        )
        self.add_action_holder(self.speed_down_action_holder)

        self.register(
            plugin_name="Mi WalkingPad",
            github_repo="https://github.com/behesse/streamcontroller-miwalkingpad",
            plugin_version="0.1.0",
            app_version="1.5.0-beta.6",
        )

        self._sync_backend_config()

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

    def get_config_rows(self) -> list[Adw.PreferencesRow]:
        settings = self.get_settings()

        self.ip_row = Adw.EntryRow(title="WalkingPad IP")
        self.ip_row.set_text(str(settings.get("walkingpad_ip", "")))

        self.token_row = Adw.EntryRow(title="WalkingPad token")
        self.token_row.set_text(str(settings.get("walkingpad_token", "")))

        self.ip_row.connect("changed", self._on_ip_changed)
        self.token_row.connect("changed", self._on_token_changed)

        return [self.ip_row, self.token_row]

    def get_settings_area(self):
        settings = self.get_settings()

        group = Adw.PreferencesGroup(title="WalkingPad Connection")

        self.ip_row = Adw.EntryRow(title="WalkingPad IP")
        self.ip_row.set_text(str(settings.get("walkingpad_ip", "")))

        self.token_row = Adw.EntryRow(title="WalkingPad token")
        self.token_row.set_text(str(settings.get("walkingpad_token", "")))

        group.add(self.ip_row)
        group.add(self.token_row)

        self.ip_row.connect("notify::text", self._on_ip_changed)
        self.token_row.connect("notify::text", self._on_token_changed)

        return group

    def _save_plugin_settings(self) -> None:
        settings = self.get_settings()
        settings["walkingpad_ip"] = self.ip_row.get_text().strip()
        settings["walkingpad_token"] = self.token_row.get_text().strip()
        self.set_settings(settings)
        self._sync_backend_config()

    def _on_ip_changed(self, *_args) -> None:
        self._save_plugin_settings()

    def _on_token_changed(self, *_args) -> None:
        self._save_plugin_settings()
