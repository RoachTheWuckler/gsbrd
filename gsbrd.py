import sys
import json
import collections
import platform
import pygame as pg
from typing import Any

IS_WINDOWS: bool = platform.system() == "Windows"
HELD_INPUTS: set[Any] = set()
INPUT_QUEUE: collections.deque[Any] = collections.deque(maxlen=2000)

if IS_WINDOWS:
    import ctypes
    VK_MAP: dict[int, str] = {
        0x01: "lmb", 0x02: "rmb", 0x04: "mmb", 0x20: "space",
        0x09: "tab", 0x0D: "return", 0x1B: "escape", 0x08: "backspace",
        0xA0: "lshift", 0xA1: "rshift", 0xA2: "lctrl", 0xA3: "rctrl",
        0xA4: "lalt", 0xA5: "ralt", 0x5B: "lwin", 0x5C: "rwin",
        0x26: "up", 0x28: "down", 0x25: "left", 0x27: "right"
    }
    for vk in range(0x41, 0x5B):
        VK_MAP[vk] = chr(vk).lower()
    for vk in range(0x30, 0x3A):
        VK_MAP[vk] = chr(vk)
else:
    from pynput import keyboard, mouse

def start_global_listeners() -> None:
    if IS_WINDOWS:
        return

    KEY_MAP: dict[keyboard.Key, str] = {
        keyboard.Key.space: "space", keyboard.Key.shift: "lshift",      
        keyboard.Key.shift_r: "rshift", keyboard.Key.ctrl: "lctrl",        
        keyboard.Key.ctrl_r: "rctrl", keyboard.Key.alt: "lalt",
        keyboard.Key.alt_gr: "ralt", keyboard.Key.cmd: "lwin",
        keyboard.Key.cmd_r: "rwin", keyboard.Key.backspace: "backspace",
        keyboard.Key.tab: "tab", keyboard.Key.enter: "return",
        keyboard.Key.caps_lock: "caps lock", keyboard.Key.esc: "escape",
        keyboard.Key.up: "up", keyboard.Key.down: "down",
        keyboard.Key.left: "left", keyboard.Key.right: "right"
    }

    def on_press(key: Any) -> None:
        if isinstance(key, keyboard.Key) and key in KEY_MAP:
            INPUT_QUEUE.append((KEY_MAP[key], True))
        elif hasattr(key, 'char') and key.char is not None:
            INPUT_QUEUE.append((str(key.char).lower(), True))

    def on_release(key: Any) -> None:
        if isinstance(key, keyboard.Key) and key in KEY_MAP:
            INPUT_QUEUE.append((KEY_MAP[key], False))
        elif hasattr(key, 'char') and key.char is not None:
            INPUT_QUEUE.append((str(key.char).lower(), False))

    def on_click(x: int, y: int, button: Any, pressed: bool) -> None:
        btn: str = "lmb" if button == mouse.Button.left else "rmb" if button == mouse.Button.right else "mmb"
        INPUT_QUEUE.append((btn, pressed))

    k_list: keyboard.Listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    k_list.daemon = True
    k_list.start()

    m_list: mouse.Listener = mouse.Listener(on_click=on_click)
    m_list.daemon = True
    m_list.start()

def update_global_inputs() -> None:
    if IS_WINDOWS:
        for vk, key_str in VK_MAP.items():
            if ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000:
                HELD_INPUTS.add(key_str)
            else:
                HELD_INPUTS.discard(key_str)
    else:
        while True:
            try:
                item: tuple[Any, ...] = INPUT_QUEUE.popleft()
                k_str: str = str(item[0])
                pressed: bool = bool(item[1])
                if pressed:
                    HELD_INPUTS.add(k_str)
                else:
                    HELD_INPUTS.discard(k_str)
            except IndexError:
                break

class Key:
    def __init__(self, pos: pg.typing.Point, scl: pg.typing.Point, disp: str, key: str) -> None:
        self.pos: pg.typing.Point = (float(pos[0]), float(pos[1]))
        self.scale: pg.typing.Point = (float(scl[0]), float(scl[1]))
        self.display: str = disp
        self.key: str = key.lower()
        self.is_held: bool = False
    
    def check_pressed(self) -> bool:
        if self.key in HELD_INPUTS:
            return True
        if self.key in ("ctrl", "control"):
            return "lctrl" in HELD_INPUTS or "rctrl" in HELD_INPUTS
        if self.key == "shift":
            return "lshift" in HELD_INPUTS or "rshift" in HELD_INPUTS
        if self.key == "alt":
            return "lalt" in HELD_INPUTS or "ralt" in HELD_INPUTS
        if self.key in ("win", "cmd", "super"):
            return "lwin" in HELD_INPUTS or "rwin" in HELD_INPUTS
            
        name_normalization: dict[str, str] = {
            "spacebar": "space", "left click": "lmb", "right click": "rmb", "middle click": "mmb"
        }
        lookup: str = name_normalization.get(self.key, self.key)
        return lookup in HELD_INPUTS
    
    def __repr__(self) -> str:
        return f"Key('{self.display}', key '{self.key}', pos {self.pos}, scale {self.scale})"

class Theme:
    def __init__(self, src: dict[str, Any]) -> None:
        self.color_bg: pg.typing.ColorLike = src["bg"]
        self.color_key_up: pg.typing.ColorLike = src["key_up"]
        self.color_key_dn: pg.typing.ColorLike = src["key_down"]

class gsbrd:
    def __init__(self, cfg_path: str) -> None:
        self.window: pg.Window = pg.Window()
        self.screen: pg.Surface = self.window.get_surface()
        self.clock: pg.time.Clock = pg.time.Clock()
        self.max_fps: int = 60
        self.is_running: bool = False

        self.window.title = "gsbrd"
        self.window.set_icon(pg.Surface((1, 1)))
        self.window.hide()

        self.cfg: dict[str, Any] = json.load(open(cfg_path, "rt"))
        validation_error: Any = self.validate_cfg()
        if validation_error is not None:
            print(f"Configuration Error: {validation_error}")
            sys.exit(1)

        self.keys: list[Key] = []
        for i, src in enumerate(self.cfg["keys"]):
            self.keys.append(Key(src["pos"], src["size"], src["label"], src["key"]))
            print(f"{i}: {self.keys[-1]}")
        
        self.font: pg.font.Font = (
            pg.Font(self.cfg["font"]["name"], self.cfg["font"]["size"]) 
            if self.cfg["font"]["local"] 
            else pg.font.SysFont(self.cfg["font"]["name"], self.cfg["font"]["size"])
        )
        
        wsize: list[float] = [0, 0]
        for key in self.keys:
            pos: pg.typing.Point = (
                key.pos[0] * (self.cfg["positioning"]["grid_x"] + self.cfg["positioning"]["grid_spacing_x"]),
                key.pos[1] * (self.cfg["positioning"]["grid_y"] + self.cfg["positioning"]["grid_spacing_y"])
            )
            scale: pg.typing.Point = (
                self.cfg["positioning"]["grid_x"] * key.scale[0] + self.cfg["positioning"]["grid_spacing_x"] * max(key.scale[0] - 1, 0),
                self.cfg["positioning"]["grid_y"] * key.scale[1] + self.cfg["positioning"]["grid_spacing_y"] * max(key.scale[1] - 1, 0)
            )
            
            bottomright: pg.typing.Point = (pos[0] + scale[0], pos[1] + scale[1])
            wsize[0] = max(wsize[0], bottomright[0])
            wsize[1] = max(wsize[1], bottomright[1])
        self.window.size = wsize
            
    
    def validate_cfg(self) -> Any:
        required_fields: list[str] = ["font", "colors", "key_style", "positioning", "keys"]
        for field in required_fields:
            if field not in self.cfg:
                return f"Config missing `{field}` field"

        if not isinstance(self.cfg["font"], dict): return "Config field `font` is invalid"
        if not isinstance(self.cfg["colors"], dict): return "Config field `colors` is invalid"
        if not isinstance(self.cfg["key_style"], dict): return "Config field `key_style` is invalid"
        if not isinstance(self.cfg["positioning"], dict): return "Config field `positioning` is invalid"
        if not isinstance(self.cfg["keys"], list): return "Config field `keys` is invalid"
        return None
    
    def handle_event(self, event: pg.event.Event) -> None:
        if event.type == pg.WINDOWCLOSE:
            self.is_running = False

    def update(self, delta: float) -> None:
        update_global_inputs()
        for key in self.keys:
            key.is_held = key.check_pressed()
    
    def render(self) -> None:
        bg_color: pg.typing.ColorLike = self.cfg["colors"]["bg"]
        self.screen.fill(bg_color)
        
        for key in self.keys:
            color: pg.typing.ColorLike = self.cfg["colors"]["key_down"] if key.is_held else self.cfg["colors"]["key_up"]
            key_color: pg.typing.ColorLike = self.cfg["colors"]["key_down_text"] if key.is_held else self.cfg["colors"]["key_up_text"]
            
            pos: pg.typing.Point = (
                key.pos[0] * (self.cfg["positioning"]["grid_x"] + self.cfg["positioning"]["grid_spacing_x"]),
                key.pos[1] * (self.cfg["positioning"]["grid_y"] + self.cfg["positioning"]["grid_spacing_y"])
            )
            scale: pg.typing.Point = (
                self.cfg["positioning"]["grid_x"] * key.scale[0] + self.cfg["positioning"]["grid_spacing_x"] * max(key.scale[0] - 1, 0),
                self.cfg["positioning"]["grid_y"] * key.scale[1] + self.cfg["positioning"]["grid_spacing_y"] * max(key.scale[1] - 1, 0)
            )
            
            if self.cfg["key_style"]["fill"]:
                pg.draw.rect(self.screen, color, (pos, scale), 0, self.cfg["key_style"]["border_radius"])
                
            outline_color: pg.typing.ColorLike = (
                max(color[0] - 20, 0),
                max(color[1] - 20, 0),
                max(color[2] - 20, 0),
            )
            pg.draw.rect(self.screen, outline_color, (pos, scale), self.cfg["key_style"]["outline_size"], self.cfg["key_style"]["border_radius"])
            
            l: pg.Surface = self.font.render(key.display, True, key_color)
            self.screen.blit(l, (
                pos[0] + scale[0] / 2 - l.width / 2,
                pos[1] + scale[1] / 2 - l.height / 2
            ))
            
    def run(self) -> None:
        if self.is_running: return
        self.is_running = True
        self.window.show()
        while self.is_running:
            delta: float = self.clock.tick(self.max_fps) / 1000.0
            for event in pg.event.get():
                if hasattr(event, "window") and event.window is not None:
                    if event.window.id == self.window.id:
                        self.handle_event(event)
                else:
                    self.handle_event(event)
            self.update(delta)
            self.render()
            self.window.flip()

def main() -> None:
    args: list[str] = sys.argv
    if len(args) != 2:
        print("Incorrect usage! Use: `python gsbrd.py <config-path>`")
        return

    start_global_listeners()

    pg.display.init()
    pg.font.init()
    app: gsbrd = gsbrd(args[1])
    app.run()
    pg.quit()

if __name__ == "__main__": main()
