import json
from typing import List, Dict

import nebulatk as ntk

from projector import Projector


WINDOW_BACKGROUND = "#181818"
FRAME_BACKGROUND = "#242424"
TEXT_COLOR = "#ffffff"
ACCENT_COLOR = "#569e6a"
ACCENT_COLOR_HOVER = "#4a845a"
DISABLED_COLOR = "#6e6e6e"
DISABLED_COLOR_HOVER = "#5a5a5a"


class ProjectorControllerFrame(ntk.Frame):
    """
    One UI controller for a single projector.

    Sections (top to bottom):
      - Name label (projector_type or friendly name)
      - Source buttons
      - Feature toggle buttons
      - Power button (icon), reflecting initial power state
    """

    def __init__(self, master, proj: Projector, meta: Dict, *args, **kwargs):
        super().__init__(master, fill=FRAME_BACKGROUND, *args, **kwargs)
        self.hide()
        self.proj = proj
        self.meta = meta

        # Pre-load power icon images (off/on with hover variants)
        self.power_icon_off = ntk.image_manager.Image("power.png")
        self.power_icon_off.recolor(DISABLED_COLOR)
        self.power_icon_off_hover = ntk.image_manager.Image("power.png")
        self.power_icon_off_hover.recolor(DISABLED_COLOR_HOVER)

        self.power_icon_on = ntk.image_manager.Image("power.png")
        self.power_icon_on.recolor(ACCENT_COLOR)
        self.power_icon_on_hover = ntk.image_manager.Image("power.png")
        self.power_icon_on_hover.recolor(ACCENT_COLOR_HOVER)

        self._build_ui()
        self._sync_initial_state()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        # Name section
        name = self.meta.get("name") or self.meta.get("projector_type", "Projector")
        self.name_label = ntk.Entry(
            self,
            text=name,
            font=("Arial", 12, "bold"),
            text_color=TEXT_COLOR,
            fill="#00000000",
        )
        self.name_label.place(x=8, y=6)

        # Source list section
        y = self._build_sources_section(y_start=30)

        # Feature list section
        self._build_features_section(y_start=y)

        # Power button on the right
        self._build_power_section(x_right=370, y_center=60+((y-70)/2))

        self.height=y+40
        
        self._update_children()

    def _build_sources_section(self, y_start: int):
        # Sources are commands where type == "source" or "source_cycle"
        commands = self.proj.projector_lib.commands
        self.source_buttons = []

        x = 8

        def build_button(x, name, cmd):
            btn = ntk.Button(
                self,
                text=name,
                font="Arial",
                width=72,
                height=24
            )

            def make_handler(command_name: str):
                def handler():
                    # Use high-level set_source where possible so Epson
                    # cycle keys behave as expected for human labels.
                    try:
                        self.proj.set_source(command_name)
                    except Exception:
                        # Fallback to raw command if mapping fails
                        try:
                            self.proj.toggle(command_name)
                        except Exception:
                            print(e,"iamanexception")

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
                    if x >= 76*3:
                        x = 8
                        y_start += 30
                    else:
                        x += 76
                    
            else:
                build_button(x, name, cmd)
                x += 76
        return y_start+40

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
                font=("Arial", 10),
                width=72,
                height=24
            )

            def make_handler(command_name: str):
                def handler():
                    try:
                        self.proj.toggle(command_name)
                    except Exception as e:
                        print(e,"iamanexception")

                return handler

            btn.command = make_handler(name)
            btn.place(x=x, y=y_start)
            self.feature_buttons.append(btn)
            x += 76

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
            # Button's active state determines desired power
            if self.power_button.state:
                self.proj.on()
            else:
                self.proj.off()

        self.power_button.command = on_power
        self.power_button.place(x=x_right - size, y=y_center - size // 2)

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
            self.power_button.clicked()
        elif (not is_on) and self.power_button.state:
            self.power_button.clicked()


def load_projectors_from_json(path: str = "data.json") -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Only use resolved projectors for full control
    return data.get("resolved", [])


def create_app():
    # Load projector definitions
    projector_defs = load_projectors_from_json()

    # Simple layout: vertical stack of controller frames
    frame_height = 120
    window_height = max(frame_height * len(projector_defs), frame_height)
    window_width = 400

    window = ntk.Window(
        title="Projector Controller", width=window_width, height=window_height
    )

    background = ntk.Frame(
        window, fill=WINDOW_BACKGROUND, width=window_width, height=window_height
    )
    background.place(-1, -1)

    for idx, meta in enumerate(projector_defs):
        ip = meta["ip"]
        proj_type = meta["projector_type"]

        proj = Projector(ip, proj_type)

        frame = ProjectorControllerFrame(
            background,
            proj,
            meta,
            width=window_width - 16,
            height=frame_height - 8,
        )
        window_height += frame.height-frame_height+10

        window.root.geometry(f"{window_width}x{window_height}")
        window.canvas.configure(height=window_height)
        window.root.update()
        background.height=window_height
        background.update()
        frame.place(x=8, y=8 + idx * frame_height)
        frame.show()
    
    return window


if __name__ == "__main__":
    app = create_app()
