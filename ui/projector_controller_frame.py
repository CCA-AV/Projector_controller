"""Primary UI frame controlling a single projector."""

import contextlib
import importlib
from typing import Dict, List, Optional

import nebulatk as ntk

from projector import Projector

from . import constants as ui_constants
from .loading_indicator import LoadingIndicator
from .simple_dropdown import SimpleDropdown


class ProjectorControllerFrame(ntk.Frame):
    """
    One UI controller for a single projector.

    Sections (top to bottom):
      - Name label (projector_type or friendly name)
      - Source buttons
      - Feature toggle buttons
      - Power button (icon), reflecting initial power state
    """

    def __init__(
        self,
        master,
        proj: Projector,
        meta: Dict,
        projector_types: Optional[List[str]] = None,
        *args,
        **kwargs,
    ):
        super().__init__(master, fill=ui_constants.FRAME_BACKGROUND, *args, **kwargs)
        self.hide()
        self.proj = proj
        self.meta = meta
        self.projector_types = projector_types or []
        self.loading_indicator = None
        self.settings_visible = False
        self.settings_inputs: Dict[str, ntk.Entry] = {}

        # Pre-load power icon images (off/on with hover variants)
        self.power_icon_off = ntk.image_manager.Image("images/power.png")
        self.power_icon_off.recolor(ui_constants.DISABLED_COLOR)
        self.power_icon_off_hover = ntk.image_manager.Image("images/power.png")
        self.power_icon_off_hover.recolor(ui_constants.DISABLED_COLOR_HOVER)

        self.power_icon_on = ntk.image_manager.Image("images/power.png")
        self.power_icon_on.recolor(ui_constants.ACCENT_COLOR)
        self.power_icon_on_hover = ntk.image_manager.Image("images/power.png")
        self.power_icon_on_hover.recolor(ui_constants.ACCENT_COLOR_HOVER)

        self.settings_icon = ntk.image_manager.Image("images/settings.png")
        self.settings_icon.recolor(ui_constants.DISABLED_COLOR)
        self.settings_icon_hover = ntk.image_manager.Image("images/settings.png")
        self.settings_icon_hover.recolor(ui_constants.DISABLED_COLOR_HOVER)
        self.settings_icon_active = ntk.image_manager.Image("images/settings.png")
        self.settings_icon_active.recolor(ui_constants.ACCENT_COLOR)
        self.settings_icon_active_hover = ntk.image_manager.Image("images/settings.png")
        self.settings_icon_active_hover.recolor(ui_constants.ACCENT_COLOR_HOVER)

        self._build_ui()
        self._configure_loading_overlay()
        self._sync_initial_state()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        # Name section
        # Prefer a stored custom name; otherwise derive a human-friendly default
        # from the projector type (e.g. "test_projector" -> "Test Projector").
        name = self.meta.get("name")
        if not name:
            proj_type = self.meta.get("projector_type", "Projector")
            name = proj_type.replace("_", " ").title()
        self.name_label = ntk.Entry(
            self,
            text=name,
            font=("Arial", 12, "bold"),
            text_color=ui_constants.TEXT_COLOR,
            fill="#00000000",
        )
        self.name_label.place(x=8, y=6)
        self.name_label.cursor.fill = "#ffffff"
        self.name_label.cursor_animation.stop()
        self.name_label.cursor_animation = ntk.animation_controller.Animation(
            self.name_label.cursor,
            {
                "fill": "#ffffff00",  # Fade out completely
            },
            duration=0.4,  # Slightly slower blink for a more natural feel
            looping=True,
        )
        self.name_label.cursor_animation.start()

        self._build_settings_trigger()

        self.max_font_size = 100
        for name, cmd in self.proj.projector_lib.commands.items():
            if cmd.get("type") not in ("source", "source_cycle", "feature", "toggle"):
                continue
            max_for_name = ntk.fonts_manager.get_max_font_size(
                self.master.root,
                ("Arial", 12, "bold"),
                ui_constants.BUTTON_WIDTH - 4,
                ui_constants.BUTTON_HEIGHT - 4,
                name,
            )
            if max_for_name < self.max_font_size:
                self.max_font_size = max_for_name

        # Source list section
        y = self._build_sources_section(y_start=30)

        # Feature list section
        self._build_features_section(y_start=y)

        # Power button on the right
        offset = ui_constants.FRAME_WIDTH - 6
        power_center = 60 + ((y - 70) / 2)
        self._build_power_section(x_right=offset, y_center=power_center)

        self.height = y + 40
        self._build_settings_panel()

    def _configure_loading_overlay(self):
        overlay_place = {"x": 0, "y": 0}
        overlay_height = getattr(self, "height", ui_constants.FRAME_HEIGHT)
        self.loading_label = ntk.Label(
            self,
            text="Loading...",
            font=("Arial", 20, "bold"),
            text_color=ui_constants.TEXT_COLOR,
            fill=f"{ui_constants.WINDOW_BACKGROUND}8F",
            width=ui_constants.FRAME_WIDTH,
            height=overlay_height,
        )
        self.loading_label.place(**overlay_place)
        self.loading_label.hide()
        self.loading_indicator = LoadingIndicator(
            self.loading_label,
            self.master.root,
            place_kwargs=overlay_place,
        )

    def _build_sources_section(self, y_start: int):
        # Sources are commands where type == "source" or "source_cycle"
        commands = self.proj.projector_lib.commands
        self.source_buttons = []

        x = 8

        def build_button(x, name, cmd):
            btn = ntk.Button(
                self,
                text=name,
                font=("Arial", self.max_font_size, "bold"),
                width=ui_constants.BUTTON_WIDTH,
                height=ui_constants.BUTTON_HEIGHT,
                border=ui_constants.DISABLED_COLOR_HOVER,
                border_width=2,
                fill=ui_constants.DISABLED_COLOR,
                hover_fill=ui_constants.DISABLED_COLOR_HOVER,
                active_fill=ui_constants.ACCENT_COLOR,
                active_hover_fill=ui_constants.ACCENT_COLOR_HOVER,
                text_color=ui_constants.TEXT_COLOR,
                mode="toggle",
            )

            def make_handler(command_name: str):
                def handler():
                    print("handler called")
                    with self._loading_context():
                        # Use high-level set_source where possible so Epson
                        # cycle keys behave as expected for human labels.
                        try:
                            self.proj.set_source(command_name)
                            self._radio_switch(btn)
                        except Exception:
                            # Fallback to raw command if mapping fails
                            try:
                                self.proj.toggle(command_name)
                                self._radio_switch(btn)
                            except Exception as e:
                                btn.state = True
                                ntk.standard_methods.toggle_object_toggle(btn)
                                print(e, "reached iamanexception")

                return handler

            btn.command = make_handler(name)
            btn.place(x=x, y=y_start)
            self.source_buttons.append(btn)
            return btn

        for name, cmd in commands.items():
            if cmd.get("type") not in ("source", "source_cycle"):
                continue

            if cmd.get("type") == "source_cycle":
                for target in self.proj.get_targets(name):
                    build_button(x, target, cmd)
                    if (
                        x
                        >= (ui_constants.BUTTON_SPACING + ui_constants.BUTTON_WIDTH) * 3
                    ):
                        x = ui_constants.FRAME_SPACING
                        y_start += (
                            ui_constants.BUTTON_SPACING + ui_constants.BUTTON_HEIGHT
                        )
                    else:
                        x += ui_constants.BUTTON_SPACING + ui_constants.BUTTON_WIDTH

            else:
                build_button(x, name, cmd)
                x += ui_constants.BUTTON_SPACING + ui_constants.BUTTON_WIDTH
        return y_start + ui_constants.BUTTON_SPACING + ui_constants.BUTTON_HEIGHT

    def _radio_switch(self, new_active_button: ntk.Button):
        for button in self.source_buttons:
            if (
                button == new_active_button
                and button.state is not True
                or button != new_active_button
                and button.state is not False
            ):
                ntk.standard_methods.toggle_object_toggle(button)

    def _build_features_section(self, y_start: int):
        # Features are commands where type == "feature" or "toggle"
        commands = self.proj.projector_lib.commands
        self.feature_buttons = []

        x = 8
        for name, cmd in commands.items():
            if cmd.get("type") not in ("feature", "toggle"):
                continue

            btn = ntk.Button(
                self,
                text=name,
                font=("Arial", self.max_font_size, "bold"),
                width=ui_constants.BUTTON_WIDTH,
                height=ui_constants.BUTTON_HEIGHT,
                fill=ui_constants.DISABLED_COLOR,
                border=ui_constants.DISABLED_COLOR_HOVER,
                border_width=2,
                hover_fill=ui_constants.DISABLED_COLOR_HOVER,
                active_fill=ui_constants.ACCENT_COLOR,
                active_hover_fill=ui_constants.ACCENT_COLOR_HOVER,
                text_color=ui_constants.TEXT_COLOR,
                mode="toggle",
            )

            def make_handler(command_name: str):
                def handler():
                    with self._loading_context():
                        try:
                            self.proj.toggle(command_name)
                        except Exception as e:
                            print(e, "iamanexception")
                            ntk.standard_methods.toggle_object_toggle(btn)

                return handler

            btn.command = make_handler(name)
            btn.place(x=x, y=y_start)
            self.feature_buttons.append(btn)
            x += ui_constants.BUTTON_SPACING + ui_constants.BUTTON_WIDTH

    def _build_power_section(self, x_right: int, y_center: int):
        # Frame width assumed 240; power button sized 48x48
        size = 48
        self.power_button = ntk.Button(
            self,
            image=self.power_icon_off,
            active_image=self.power_icon_on,
            hover_image=self.power_icon_off_hover,
            active_hover_image=self.power_icon_on_hover,
            width=size,
            height=size,
            mode="toggle",
            bounds_type="box",
        )

        def on_power():
            with self._loading_context():
                # Button's active state determines desired power
                if self.power_button.state:
                    self.proj.on()
                else:
                    self.proj.off()

                self._sync_initial_state()

        self.power_button.command = on_power
        self.power_button.place(x=x_right - size, y=y_center - size // 2)

    def _build_settings_trigger(self):
        size = 20
        self.settings_button = ntk.Button(
            self,
            image=self.settings_icon,
            hover_image=self.settings_icon_hover,
            active_image=self.settings_icon_active,
            active_hover_image=self.settings_icon_active_hover,
            width=size,
            height=size,
            mode="standard",
            bounds_type="box",
        )
        self.settings_button.command = self._toggle_settings_panel
        self.settings_button.place(x=ui_constants.FRAME_WIDTH - size - 5, y=4)

    def _build_settings_panel(self):
        overlay_height = getattr(self, "height", ui_constants.FRAME_HEIGHT)
        self.settings_backdrop = ntk.Frame(
            self,
            width=ui_constants.FRAME_WIDTH,
            height=overlay_height,
            fill="#00000088",
            border_width=0,
        )
        self.settings_backdrop.hide()
        self.settings_backdrop.place(x=0, y=0)
        self.settings_backdrop.can_click = True
        self.settings_backdrop.command = lambda: self._toggle_settings_panel(False)

        panel_width = ui_constants.FRAME_WIDTH - 12
        panel_height = min(overlay_height - 8, 104)
        self.settings_panel = ntk.Frame(
            self,
            width=panel_width,
            height=panel_height,
            fill=ui_constants.SETTINGS_PANEL_FILL,
            border=ui_constants.SETTINGS_BORDER_COLOR,
            border_width=2,
        )
        panel_x = (ui_constants.FRAME_WIDTH - panel_width) // 2
        panel_y = 0
        self.settings_panel.hide()
        self.settings_panel.place(x=panel_x, y=panel_y)

        content_x = 8
        content_y = 3
        column_gap = 8
        entry_height = 24
        column_width = (panel_width - content_x * 2 - column_gap) / 2
        row_height = 38

        def place_entry(
            label_text: str, key: str, default_value: str, x: float, y: float
        ):
            label = ntk.Label(
                self.settings_panel,
                text=label_text,
                font=("Arial", 10, "bold"),
                justify="left",
                text_color=ui_constants.TEXT_COLOR,
                fill="#00000000",
            )
            label.place(x=x, y=y)
            entry = ntk.Entry(
                self.settings_panel,
                width=column_width,
                height=entry_height,
                font=("Arial", 11),
                justify="left",
                text_color=ui_constants.TEXT_COLOR,
                fill="#2c2c2c",
                border=ui_constants.SETTINGS_BORDER_COLOR,
                border_width=2,
            )
            entry.place(x=x, y=y + 16)

            entry.cursor.fill = "#ffffff"
            entry.cursor_animation.stop()
            entry.cursor_animation = ntk.animation_controller.Animation(
                entry.cursor,
                {
                    "fill": "#ffffff00",
                },
                duration=0.4,
                looping=True,
            )
            entry.cursor_animation.start()
            self.settings_inputs[key] = entry
            self._set_entry_text(entry, default_value)
            return entry

        # Row 1: IP + Projector Type
        place_entry(
            "IP Address", "ip", str(self.meta.get("ip", "")), content_x, content_y
        )

        dropdown_label_x = content_x + column_width + column_gap
        dropdown_label = ntk.Label(
            self.settings_panel,
            text="Projector Type",
            font=("Arial", 10, "bold"),
            justify="left",
            text_color=ui_constants.TEXT_COLOR,
            fill="#00000000",
        )

        dropdown_options = (
            self.projector_types[:]
            if self.projector_types
            else [self.meta.get("projector_type", "")]
        )
        dropdown_initial = self.meta.get("projector_type", dropdown_options[0])

        # Row 2: Username + Password
        second_row_y = content_y + row_height
        place_entry(
            "Username",
            "username",
            str(self.meta.get("username", "") or ""),
            content_x,
            second_row_y,
        )
        password_entry = place_entry(
            "Password",
            "password",
            str(self.meta.get("password", "") or ""),
            dropdown_label_x,
            second_row_y,
        )
        dropdown_label.place(x=dropdown_label_x, y=content_y)
        self.classification_dropdown = SimpleDropdown(
            self.settings_panel,
            options=[opt for opt in dropdown_options if opt],
            initial_value=dropdown_initial,
            width=column_width,
            height=entry_height,
            password_entry=password_entry,
        )
        self.classification_dropdown.place(x=dropdown_label_x, y=content_y + 16)

        self.settings_message_label = ntk.Label(
            self.settings_panel,
            text="",
            font=("Arial", 10),
            justify="left",
            text_color=ui_constants.SETTINGS_MESSAGE_COLOR,
            fill="#00000000",
        )
        message_y = second_row_y + row_height - 6
        self.settings_message_label.place(x=content_x, y=message_y)
        self.settings_message_label.hide()
        button_y = message_y + 12

        self.save_settings_button = ntk.Button(
            self.settings_panel,
            text="Save",
            font=("Arial", 9, "bold"),
            width=75,
            height=16,
            fill=ui_constants.ACCENT_COLOR,
            hover_fill=ui_constants.ACCENT_COLOR_HOVER,
            text_color=ui_constants.TEXT_COLOR,
        )
        self.save_settings_button.command = self._on_settings_save
        self.save_settings_button.place(x=content_x, y=button_y)

        self.cancel_settings_button = ntk.Button(
            self.settings_panel,
            text="Cancel",
            font=("Arial", 9, "bold"),
            width=75,
            height=16,
            fill=ui_constants.DISABLED_COLOR,
            hover_fill=ui_constants.DISABLED_COLOR_HOVER,
            text_color=ui_constants.TEXT_COLOR,
        )
        self.cancel_settings_button.command = self._on_settings_cancel
        self.cancel_settings_button.place(x=content_x + 85, y=button_y)

        final_panel_height = button_y + 18
        self.settings_panel.height = final_panel_height
        self._refresh_settings_overlay_size()
        self.settings_panel.hide()

    def _set_entry_text(self, entry: ntk.Entry, value: str):
        normalized = value or ""
        entry.entire_text = normalized
        entry.text = normalized
        entry.slice = [0, len(normalized)]
        entry.cursor_position = len(normalized)
        entry.update()

    def _populate_settings_fields(self):
        self._set_entry_text(self.settings_inputs["ip"], self.meta.get("ip", ""))
        self._set_entry_text(
            self.settings_inputs["username"], self.meta.get("username", "") or ""
        )
        self._set_entry_text(
            self.settings_inputs["password"], self.meta.get("password", "") or ""
        )
        dropdown_value = self.meta.get("projector_type") or (
            self.projector_types[0]
            if self.projector_types
            else self.classification_dropdown.get()
        )
        self.classification_dropdown.set_value(dropdown_value)
        self._show_settings_message("")

    def _toggle_settings_panel(self, show: Optional[bool] = None):
        target_state = not self.settings_visible if show is None else show
        if target_state:
            self._refresh_settings_overlay_size()
            self._populate_settings_fields()
            self.settings_backdrop.show()
            self.settings_panel.show()
        else:
            self.settings_backdrop.hide()
            self.settings_panel.hide()
            self.classification_dropdown.hide_options()
        self.settings_visible = target_state

    def _refresh_settings_overlay_size(self):
        if not hasattr(self, "settings_backdrop"):
            return
        self.settings_backdrop.width = ui_constants.FRAME_WIDTH
        self.settings_backdrop.height = self.height
        if hasattr(self, "settings_panel"):
            panel_width = self.settings_panel.width
            panel_height = self.settings_panel.height
            panel_x = (ui_constants.FRAME_WIDTH - panel_width) // 2
            panel_y = 0
            self.settings_panel.place(x=panel_x, y=panel_y)

    def _on_settings_save(self):
        ip_value = self.settings_inputs["ip"].get().strip()
        username_value = self.settings_inputs["username"].get().strip()
        password_value = self.settings_inputs["password"].get().strip()
        projector_type = self.classification_dropdown.get()

        if not ip_value:
            self._show_settings_message("IP address is required.")
            return
        if not projector_type:
            self._show_settings_message("Select a projector type.")
            return

        self.meta["ip"] = ip_value
        self.meta["projector_type"] = projector_type
        self.meta["username"] = username_value
        self.meta["password"] = password_value

        self.proj.ip = ip_value
        self.proj._username_override = username_value or None
        self.proj._password_override = password_value or None
        self._apply_projector_type(projector_type)

        self._toggle_settings_panel(False)

    def _apply_projector_type(self, projector_type: str):
        if not projector_type:
            return
        if getattr(self.proj, "projector_type", None) == projector_type:
            return
        self.proj.projector_type = projector_type
        self.proj.projector_lib = importlib.import_module(
            f"projectors.{projector_type}"
        )

    def _on_settings_cancel(self):
        self._populate_settings_fields()
        self._toggle_settings_panel(False)

    def _show_settings_message(self, message: str, error: bool = True):
        if not hasattr(self, "settings_message_label"):
            return
        if not message:
            self.settings_message_label.hide()
            return
        color = (
            ui_constants.SETTINGS_MESSAGE_COLOR if error else ui_constants.ACCENT_COLOR
        )
        self.settings_message_label.configure(text=message, text_color=color)
        self.settings_message_label.show()

    def export_settings(self) -> Dict[str, str]:
        return {
            "name": str(self.name_label.get() or "").strip(),
            "ip": self.meta.get("ip", ""),
            "projector_type": self.meta.get("projector_type", ""),
            "username": self.meta.get("username", "") or "",
            "password": self.meta.get("password", "") or "",
        }

    # ----------------------------------------------------------------- State
    def _sync_initial_state(self):
        """
        Query the projector and update power button and any other default state.
        """
        try:
            is_on = self.proj.status()
        except Exception:
            is_on = False

        if is_on and not self.power_button.state:
            # Toggle to "on" without triggering callback
            ntk.standard_methods.toggle_object_toggle(self.power_button)
        elif (not is_on) and self.power_button.state:
            ntk.standard_methods.toggle_object_toggle(self.power_button)

        try:
            current_source = self.proj.source()
        except Exception as e:
            print(e, "iamanexception")
            current_source = None
        print(current_source)
        if current_source:
            for button in self.source_buttons:
                if button.text.lower().replace(
                    " ", ""
                ) == current_source.lower().replace(" ", ""):
                    self._radio_switch(button)
                    break

    def _loading_context(self):
        return self.loading_indicator or contextlib.nullcontext()
