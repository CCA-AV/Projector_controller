import contextlib
import importlib
import json
from pathlib import Path
from typing import List, Dict, Optional

import nebulatk as ntk

from projector import Projector


WINDOW_BACKGROUND = "#181818"
FRAME_BACKGROUND = "#242424"
TEXT_COLOR = "#ffffff"
ACCENT_COLOR = "#569e6a"
ACCENT_COLOR_HOVER = "#3e734c"
DISABLED_COLOR = "#6e6e6e"
DISABLED_COLOR_HOVER = "#4a4a4a"
SETTINGS_PANEL_FILL = "#1e1e1e"
SETTINGS_BORDER_COLOR = "#3a3a3a"
SETTINGS_MESSAGE_COLOR = "#d36c6c"

WINDOW_WIDTH = 480
WINDOW_HEIGHT = 120
FRAME_SPACING = 8
FRAME_WIDTH = WINDOW_WIDTH - FRAME_SPACING * 2
FRAME_HEIGHT = WINDOW_HEIGHT - FRAME_SPACING * 2


BUTTON_SPACING = 4
BUTTON_WIDTH = ((FRAME_WIDTH - 70) / 4) - BUTTON_SPACING
BUTTON_HEIGHT = 30


def list_projector_types() -> List[str]:
    projectors_dir = Path("projectors")
    if not projectors_dir.exists():
        return []
    types = []
    for file in projectors_dir.glob("*.py"):
        if file.name.startswith("_"):
            continue
        stem = file.stem
        if stem == "__init__":
            continue
        types.append(stem)
    return sorted(set(types))


class SimpleDropdown(ntk.Frame):
    """Minimal dropdown built from frames/labels toggled via show/hide."""

    def __init__(
        self,
        master,
        options: List[str],
        initial_value: str = "",
        width: int = 180,
        height: int = 30,
        command=None,
        password_entry=None,
    ):
        super().__init__(
            master,
            width=width,
            height=height,
            fill=DISABLED_COLOR,
            border=DISABLED_COLOR_HOVER,
            border_width=2,
        )
        self.password_entry = password_entry
        self.can_hover = True
        self.can_click = True
        self.command = self.toggle_options
        self.option_height = height
        self.options = options[:] if options else []
        self._ensure_initial_option(initial_value)
        self.value = initial_value or (self.options[0] if self.options else "")
        self._options_visible = False

        self.display_label = ntk.Label(
            self,
            text=self._format_value(self.value),
            font=("Arial", 11),
            justify="left",
            text_color=TEXT_COLOR,
            fill="#00000000",
        )
        self.display_label.place(x=8, y=2)
        self.display_label.can_click = True
        self.display_label.command = self.toggle_options

        self.caret_label = ntk.Label(
            self,
            text="v",
            font=("Arial", 12, "bold"),
            text_color=TEXT_COLOR,
            fill="#00000000",
        )
        self.caret_label.place(x=width - 20, y=2)
        self.caret_label.can_click = True
        self.caret_label.command = self.toggle_options

        self.options_frame = ntk.Frame(
            master,
            width=width,
            height=self.option_height * max(1, len(self.options)),
            fill=SETTINGS_PANEL_FILL,
            border=SETTINGS_BORDER_COLOR,
            border_width=2,
        )
        self.option_labels: List[ntk.Label] = []
        for idx, option in enumerate(self.options):
            label = ntk.Button(
                self.options_frame,
                text=self._format_value(option),
                font=("Arial", 10),
                justify="left",
                fill="#00000000",
                hover_fill=DISABLED_COLOR_HOVER,
                text_color=TEXT_COLOR,
                width=width - 16,
            )
            label.place(x=8, y=idx * self.option_height + 2)
            label.command = self._make_option_handler(option)
            self.option_labels.append(label)
        if not self.options:
            placeholder = ntk.Label(
                self.options_frame,
                text="No options",
                font=("Arial", 10),
                justify="left",
                fill="#00000000",
                text_color=TEXT_COLOR,
            )
            placeholder.place(x=8, y=6)
            self.option_labels.append(placeholder)
        self.options_frame.hide()

    def place(self, x=0, y=0):
        super().place(x=x, y=y)
        self._update_options_position()
        return self

    def _ensure_initial_option(self, initial_value: str):
        if initial_value and initial_value not in self.options:
            self.options.insert(0, initial_value)

    def _format_value(self, value: str) -> str:
        return value.replace("_", " ").title() if value else ""

    def _make_option_handler(self, option: str):
        def handler():
            self.set_value(option)
            self.hide_options()

        return handler

    def set_value(self, value: str):
        if value and value not in self.options:
            self.options.append(value)
        self.value = value
        self.display_label.configure(text=self._format_value(value))

    def get(self) -> str:
        return self.value

    def toggle_options(self):
        if self._options_visible:
            self.hide_options()
            if self.password_entry:
                self.password_entry.show()
        else:
            self._update_options_position()
            if self.password_entry:
                self.password_entry.hide()
            self.options_frame.show()
            self._options_visible = True

    def hide_options(self):
        self.options_frame.hide()
        self._options_visible = False
        if self.password_entry:
            self.password_entry.show()

    def _update_options_position(self):
        self.options_frame.place(x=self.x, y=self.y + self.height)


class LoadingIndicator:
    """
    Simple reference-counted loading indicator controller.
    Shows the provided label while one or more commands are active.
    """

    def __init__(self, label: ntk.Label, root, place_kwargs: Optional[Dict] = None):
        self.label = label
        self.root = root
        self._active = 0
        self._place_kwargs = place_kwargs or {}

    def __enter__(self):
        print("entering loading context")
        self._active += 1
        if self._active == 1:
            if self._place_kwargs:
                self.label.place(**self._place_kwargs)
            self.label.show()
            self.label.update()
            self.label.master.update()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._active > 0:
            self._active -= 1
        if self._active == 0:
            self.label.hide()
        return False


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
        super().__init__(master, fill=FRAME_BACKGROUND, *args, **kwargs)
        self.hide()
        self.proj = proj
        self.meta = meta
        self.projector_types = projector_types or []
        self.loading_indicator = None
        self.settings_visible = False
        self.settings_inputs: Dict[str, ntk.Entry] = {}

        # Pre-load power icon images (off/on with hover variants)
        self.power_icon_off = ntk.image_manager.Image("images/power.png")
        self.power_icon_off.recolor(DISABLED_COLOR)
        self.power_icon_off_hover = ntk.image_manager.Image("images/power.png")
        self.power_icon_off_hover.recolor(DISABLED_COLOR_HOVER)

        self.power_icon_on = ntk.image_manager.Image("images/power.png")
        self.power_icon_on.recolor(ACCENT_COLOR)
        self.power_icon_on_hover = ntk.image_manager.Image("images/power.png")
        self.power_icon_on_hover.recolor(ACCENT_COLOR_HOVER)

        self.settings_icon = ntk.image_manager.Image("images/settings.png")
        self.settings_icon.recolor(DISABLED_COLOR)
        self.settings_icon_hover = ntk.image_manager.Image("images/settings.png")
        self.settings_icon_hover.recolor(DISABLED_COLOR_HOVER)
        self.settings_icon_active = ntk.image_manager.Image("images/settings.png")
        self.settings_icon_active.recolor(ACCENT_COLOR)
        self.settings_icon_active_hover = ntk.image_manager.Image("images/settings.png")
        self.settings_icon_active_hover.recolor(ACCENT_COLOR_HOVER)

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
            text_color=TEXT_COLOR,
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
                BUTTON_WIDTH - 4,
                BUTTON_HEIGHT - 4,
                name,
            )
            if max_for_name < self.max_font_size:
                self.max_font_size = max_for_name

        # Source list section
        y = self._build_sources_section(y_start=30)

        # Feature list section
        self._build_features_section(y_start=y)

        # Power button on the right
        self._build_power_section(x_right=FRAME_WIDTH - 6, y_center=60 + ((y - 70) / 2))

        self.height = y + 40
        self._build_settings_panel()

    def _configure_loading_overlay(self):
        overlay_place = {"x": 0, "y": 0}
        overlay_height = getattr(self, "height", FRAME_HEIGHT)
        self.loading_label = ntk.Label(
            self,
            text="Loading...",
            font=("Arial", 20, "bold"),
            text_color=TEXT_COLOR,
            fill=f"{WINDOW_BACKGROUND}8F",
            width=FRAME_WIDTH,
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
                width=BUTTON_WIDTH,
                height=BUTTON_HEIGHT,
                border=DISABLED_COLOR_HOVER,
                border_width=2,
                fill=DISABLED_COLOR,
                hover_fill=DISABLED_COLOR_HOVER,
                active_fill=ACCENT_COLOR,
                active_hover_fill=ACCENT_COLOR_HOVER,
                text_color=TEXT_COLOR,
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
                    if x >= (BUTTON_SPACING + BUTTON_WIDTH) * 3:
                        x = FRAME_SPACING
                        y_start += BUTTON_SPACING + BUTTON_HEIGHT
                    else:
                        x += BUTTON_SPACING + BUTTON_WIDTH

            else:
                build_button(x, name, cmd)
                x += BUTTON_SPACING + BUTTON_WIDTH
        return y_start + BUTTON_SPACING + BUTTON_HEIGHT

    def _radio_switch(self, new_active_button: ntk.Button):
        for button in self.source_buttons:
            if (
                button == new_active_button
                and button.state != True
                or button != new_active_button
                and button.state != False
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
                width=BUTTON_WIDTH,
                height=BUTTON_HEIGHT,
                fill=DISABLED_COLOR,
                border=DISABLED_COLOR_HOVER,
                border_width=2,
                hover_fill=DISABLED_COLOR_HOVER,
                active_fill=ACCENT_COLOR,
                active_hover_fill=ACCENT_COLOR_HOVER,
                text_color=TEXT_COLOR,
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
            x += BUTTON_SPACING + BUTTON_WIDTH

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
        )
        self.settings_button.command = self._toggle_settings_panel
        self.settings_button.place(x=FRAME_WIDTH - size - 5, y=4)

    def _build_settings_panel(self):
        overlay_height = getattr(self, "height", FRAME_HEIGHT)
        self.settings_backdrop = ntk.Frame(
            self,
            width=FRAME_WIDTH,
            height=overlay_height,
            fill="#00000088",
            border_width=0,
        )
        self.settings_backdrop.hide()
        self.settings_backdrop.place(x=0, y=0)
        self.settings_backdrop.can_click = True
        self.settings_backdrop.command = lambda: self._toggle_settings_panel(False)

        panel_width = FRAME_WIDTH - 12
        panel_height = min(overlay_height - 8, 104)
        self.settings_panel = ntk.Frame(
            self,
            width=panel_width,
            height=panel_height,
            fill=SETTINGS_PANEL_FILL,
            border=SETTINGS_BORDER_COLOR,
            border_width=2,
        )
        panel_x = (FRAME_WIDTH - panel_width) // 2
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
                text_color=TEXT_COLOR,
                fill="#00000000",
            )
            label.place(x=x, y=y)
            entry = ntk.Entry(
                self.settings_panel,
                width=column_width,
                height=entry_height,
                font=("Arial", 11),
                justify="left",
                text_color=TEXT_COLOR,
                fill="#2c2c2c",
                border=SETTINGS_BORDER_COLOR,
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
            text_color=TEXT_COLOR,
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
            text_color=SETTINGS_MESSAGE_COLOR,
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
            fill=ACCENT_COLOR,
            hover_fill=ACCENT_COLOR_HOVER,
            text_color=TEXT_COLOR,
        )
        self.save_settings_button.command = self._on_settings_save
        self.save_settings_button.place(x=content_x, y=button_y)

        self.cancel_settings_button = ntk.Button(
            self.settings_panel,
            text="Cancel",
            font=("Arial", 9, "bold"),
            width=75,
            height=16,
            fill=DISABLED_COLOR,
            hover_fill=DISABLED_COLOR_HOVER,
            text_color=TEXT_COLOR,
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
        self.settings_backdrop.width = FRAME_WIDTH
        self.settings_backdrop.height = self.height
        if hasattr(self, "settings_panel"):
            panel_width = self.settings_panel.width
            panel_height = self.settings_panel.height
            panel_x = (FRAME_WIDTH - panel_width) // 2
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
        color = SETTINGS_MESSAGE_COLOR if error else ACCENT_COLOR
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


def load_projectors_from_json(path: str = "data.json") -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Only use resolved projectors for full control
    return data.get("resolved", [])


def create_app():
    # Load projector definitions
    projector_defs = load_projectors_from_json()
    projector_types = list_projector_types()

    # Simple layout: vertical stack of controller frames
    frames = []
    frame_height = FRAME_HEIGHT
    window_height = max(frame_height * len(projector_defs), frame_height)
    window_width = WINDOW_WIDTH

    def _save_names_and_close():
        """
        Persist any edited projector names back to data.json before closing.
        """
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        resolved = data.get("resolved", [])

        # Update entries in order; if the JSON has fewer entries than frames,
        # update only what exists.
        for idx, frame in enumerate(frames):
            if idx >= len(resolved):
                break
            frame_data = frame.export_settings()
            resolved[idx].update(frame_data)

        data["resolved"] = resolved

        with contextlib.suppress(Exception):
            with open("data.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    window = ntk.Window(
        title="Projector Controller",
        width=window_width,
        height=window_height,
        closing_command=_save_names_and_close,
    )
    window.updates_all = False

    background = ntk.Frame(
        window,
        fill=WINDOW_BACKGROUND,
        width=window_width,
        height=window_height,
    )
    background.place()

    for idx, meta in enumerate(projector_defs):
        print("creating frame for", meta["name"])
        ip = meta["ip"]
        proj_type = meta["projector_type"]
        username = meta.get("username")
        password = meta.get("password")

        proj = Projector(ip, proj_type, username=username, password=password)

        frame = ProjectorControllerFrame(
            background,
            proj,
            meta,
            projector_types=projector_types,
            width=FRAME_WIDTH,
            height=FRAME_HEIGHT,
        )
        frames.append(frame)
        window_height += frame.height - FRAME_HEIGHT + FRAME_SPACING * 2

        frame.place(
            x=FRAME_SPACING, y=FRAME_SPACING + idx * (FRAME_HEIGHT + FRAME_SPACING)
        )
        frame.show()
    background.configure(height=window_height)
    window.resize(window_width, window_height)
    return window


if __name__ == "__main__":
    app = create_app()
