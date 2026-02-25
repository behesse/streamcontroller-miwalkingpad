import os

import gi
from gi.repository import GLib, Gtk

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
        self._last_saved_device_id = ""
        self._discovered_devices: list[dict] = []
        self._discovered_device_ids: list[str] = []
        self._discovery_in_progress = False

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
        return Gtk.Image.new_from_file(self.get_asset_path("icon.png"))

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
        device_id = str(settings.get("walkingpad_device_id", "")).strip()

        try:
            if self.backend is not None:
                self.backend.configure(ip=ip, token=token, device_id=device_id)
        except Exception:
            # Backend may still be starting.
            pass

    def get_settings_area(self):
        settings = self.get_settings()

        self._last_saved_ip = str(settings.get("walkingpad_ip", "")).strip()
        self._last_saved_token = str(settings.get("walkingpad_token", "")).strip()
        self._last_saved_device_id = str(settings.get("walkingpad_device_id", "")).strip()

        group = Adw.PreferencesGroup(title="WalkingPad Connection")

        self.ip_row = Adw.EntryRow(title="WalkingPad IP")
        self.ip_row.set_text(str(settings.get("walkingpad_ip", "")))

        self.token_row = Adw.EntryRow(title="WalkingPad token")
        self.token_row.set_text(str(settings.get("walkingpad_token", "")))

        self.device_id_row = Adw.EntryRow(title="WalkingPad device_id")
        self.device_id_row.set_text(str(settings.get("walkingpad_device_id", "")))

        self.discovery_row = Adw.ActionRow(title="Discover devices")
        self.discovery_button = Gtk.Button(label="Discover")
        self.discovery_button.connect("clicked", self._on_discover_clicked)
        self.discovery_row.add_suffix(self.discovery_button)

        self.discovery_select_row = Adw.ActionRow(title="Discovered WalkingPads")
        self.discovery_model = Gtk.StringList.new(["No devices discovered yet"])
        self.discovery_dropdown = Gtk.DropDown(model=self.discovery_model)
        self.discovery_dropdown.set_sensitive(False)
        self.discovery_dropdown.connect("notify::selected", self._on_discovery_selected)
        self.discovery_select_row.add_suffix(self.discovery_dropdown)
        self.discovery_select_row.set_activatable(False)

        group.add(self.ip_row)
        group.add(self.token_row)
        group.add(self.device_id_row)
        group.add(self.discovery_row)
        group.add(self.discovery_select_row)

        self.ip_row.connect("changed", self._on_ip_changed)
        self.token_row.connect("changed", self._on_token_changed)
        self.device_id_row.connect("changed", self._on_device_id_changed)
        self.ip_row.connect("apply", self._on_ip_changed)
        self.token_row.connect("apply", self._on_token_changed)
        self.device_id_row.connect("apply", self._on_device_id_changed)
        self.ip_row.connect("notify::has-focus", self._on_ip_focus_changed)
        self.token_row.connect("notify::has-focus", self._on_token_focus_changed)
        self.device_id_row.connect("notify::has-focus", self._on_device_id_focus_changed)

        return group

    def _save_plugin_settings(self) -> None:
        ip = self.ip_row.get_text().strip()
        token = self.token_row.get_text().strip()
        device_id = self.device_id_row.get_text().strip()

        if (
            ip == self._last_saved_ip
            and token == self._last_saved_token
            and device_id == self._last_saved_device_id
        ):
            return

        settings = self.get_settings()
        settings["walkingpad_ip"] = ip
        settings["walkingpad_token"] = token
        settings["walkingpad_device_id"] = device_id
        self.set_settings(settings)

        self._last_saved_ip = ip
        self._last_saved_token = token
        self._last_saved_device_id = device_id
        self._sync_backend_config()

    def _set_discovered_devices(self, devices: list[dict]) -> None:
        self._discovered_devices = devices
        self._discovered_device_ids = []

        labels = []
        for entry in devices:
            model = str(entry.get("model", "") or "")
            ip = str(entry.get("ip", "") or "")
            device_id = str(entry.get("device_id", "") or "")
            labels.append(f"{model} — {ip} — {device_id}")
            self._discovered_device_ids.append(device_id)

        if not labels:
            labels = ["No compatible WalkingPad found"]
            self.discovery_dropdown.set_sensitive(False)
        else:
            self.discovery_dropdown.set_sensitive(True)

        self.discovery_model.splice(0, self.discovery_model.get_n_items(), labels)
        selected_device_id = self.device_id_row.get_text().strip()
        selected_idx = 0
        if selected_device_id and selected_device_id in self._discovered_device_ids:
            selected_idx = self._discovered_device_ids.index(selected_device_id)

        self.discovery_dropdown.set_selected(selected_idx)
        self._apply_discovery_selection(selected_idx)

    def _apply_discovery_selection(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._discovered_devices):
            return

        chosen = self._discovered_devices[idx]
        device_id = str(chosen.get("device_id", "") or "").strip()
        if not device_id:
            return

        if self.device_id_row.get_text().strip() == device_id:
            return

        self.device_id_row.set_text(device_id)
        self._save_plugin_settings()

    def _on_discover_clicked(self, *_args) -> None:
        if self._discovery_in_progress:
            return

        token = self.token_row.get_text().strip()
        if not token:
            self.show_error("Discovery requires token")
            return

        if self.backend is None:
            self.show_error("Backend not ready")
            return

        self._discovery_in_progress = True
        self.discovery_button.set_sensitive(False)

        GLib.Thread.new("miwalkingpad-discovery", self._discover_devices_worker, token)

    def _discover_devices_worker(self, token: str) -> None:
        result: dict | None = None
        error: str | None = None

        try:
            result = self.backend.discover_devices(token=token, timeout=5)
        except Exception as exc:  # noqa: BLE001
            error = str(exc)

        GLib.idle_add(self._on_discovery_finished, result, error)

    def _on_discovery_finished(self, result: dict | None, error: str | None) -> bool:
        self._discovery_in_progress = False
        self.discovery_button.set_sensitive(True)

        if error is not None:
            self.show_error(f"Discovery failed: {error}")
            return False

        result = result or {}
        if not result.get("ok", False):
            self.show_error(str(result.get("error", "Discovery failed")))
            self._set_discovered_devices([])
            return False

        devices = result.get("devices", []) or []
        self._set_discovered_devices(devices)
        return False

    def _on_discovery_selected(self, *_args) -> None:
        idx = int(self.discovery_dropdown.get_selected())
        self._apply_discovery_selection(idx)

    def _on_ip_changed(self, *_args) -> None:
        self._save_plugin_settings()

    def _on_token_changed(self, *_args) -> None:
        self._save_plugin_settings()

    def _on_device_id_changed(self, *_args) -> None:
        self._save_plugin_settings()

    def _on_ip_focus_changed(self, row, _param) -> None:
        if not row.get_has_focus():
            self._save_plugin_settings()

    def _on_token_focus_changed(self, row, _param) -> None:
        if not row.get_has_focus():
            self._save_plugin_settings()

    def _on_device_id_focus_changed(self, row, _param) -> None:
        if not row.get_has_focus():
            self._save_plugin_settings()
