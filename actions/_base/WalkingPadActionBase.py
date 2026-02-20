from __future__ import annotations

from src.backend.PluginManager.ActionBase import ActionBase


class WalkingPadActionBase(ActionBase):
    ICON_SIZE_DEFAULT = 0.6
    ICON_SIZE_LARGE = 0.75

    def set_icon(self, icon_key: str, size: float | None = None) -> None:
        icon_size = size or self.ICON_SIZE_DEFAULT
        _meta, rendered = self.plugin_base.asset_manager.icons.get_asset_values(icon_key)
        if rendered is None:
            raise RuntimeError(f"missing_icon_asset_key:{icon_key}")
        self.set_media(image=rendered, size=icon_size)

    def clear_labels(self) -> None:
        self.set_top_label("")
        self.set_center_label("")
        self.set_bottom_label("")

    def get_backend(self):
        plugin = getattr(self, "plugin_base", None)
        if plugin is None:
            return None
        return getattr(plugin, "backend", None)

    def get_backend_status(self) -> dict | None:
        backend = self.get_backend()
        if backend is None:
            return None
        try:
            return backend.get_status()
        except Exception:
            return None
