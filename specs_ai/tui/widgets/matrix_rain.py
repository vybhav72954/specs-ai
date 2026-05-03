"""Matrix digital rain gutter columns."""

import random

from rich.text import Text
from textual.widget import Widget


# Character pool: katakana range, ASCII digits, Latin uppercase, symbols
_CHAR_POOL: list[str] = (
    [chr(c) for c in range(0x30A0, 0x30FF + 1)]
    + list("0123456789")
    + list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    + list("@#$%&*")
)

# Color gradient from bright head to dim tail
_HEAD_COLOR = "#00FF41"
_TRAIL_COLORS = [
    "#00DD38",
    "#00BB2F",
    "#009926",
    "#00771D",
    "#005514",
    "#00330B",
    "#001A06",
]


class _Stream:
    """A single falling column of characters."""

    def __init__(self, height: int) -> None:
        self.height = height
        self.length = random.randint(6, 14)
        self.head = random.randint(-self.length, height // 3)
        self.chars = [random.choice(_CHAR_POOL) for _ in range(self.length)]
        self.delay = 0

    def advance(self) -> None:
        """Move the stream down by one row."""
        if self.delay > 0:
            self.delay -= 1
            return
        self.head += 1
        # Randomize the head character each tick for that flickering effect
        self.chars[0] = random.choice(_CHAR_POOL)
        if self.head - self.length > self.height:
            self.reset()

    def reset(self) -> None:
        """Respawn at the top after a random delay."""
        self.head = random.randint(-self.length, 0)
        self.length = random.randint(6, 14)
        self.chars = [random.choice(_CHAR_POOL) for _ in range(self.length)]
        self.delay = random.randint(0, 8)  # 0-1s at ~8 FPS


class MatrixRain(Widget):
    """A narrow column of falling Matrix-style characters."""

    DEFAULT_CSS = """
    MatrixRain {
        width: 3;
        height: 100%;
        background: #0A0A0A;
    }
    """

    def __init__(self, columns: int = 2, **kwargs) -> None:
        super().__init__(**kwargs)
        self._columns = columns
        self._streams: list[list[_Stream]] = []

    def on_mount(self) -> None:
        """Initialize streams and start the animation timer."""
        height = self.size.height or 30
        self._streams = [
            [_Stream(height) for _ in range(1)]
            for _ in range(self._columns)
        ]
        self.set_interval(1 / 8, self._tick)

    def on_resize(self) -> None:
        """Reinitialize streams when terminal is resized."""
        height = self.size.height or 30
        self._streams = [
            [_Stream(height) for _ in range(1)]
            for _ in range(self._columns)
        ]

    def _tick(self) -> None:
        """Advance all streams and refresh the display."""
        for col_streams in self._streams:
            for stream in col_streams:
                stream.advance()
        self.refresh()

    def render(self) -> Text:
        """Render all streams as styled Rich Text."""
        height = self.size.height or 30
        # Build a grid: rows x columns
        grid: list[list[tuple[str, str]]] = [
            [(" ", "#0A0A0A") for _ in range(self._columns)]
            for _ in range(height)
        ]

        for col_idx, col_streams in enumerate(self._streams):
            for stream in col_streams:
                for i in range(stream.length):
                    row = stream.head - i
                    if 0 <= row < height:
                        char = stream.chars[i % len(stream.chars)]
                        if i == 0:
                            color = _HEAD_COLOR
                        elif i < len(_TRAIL_COLORS):
                            color = _TRAIL_COLORS[i]
                        else:
                            color = _TRAIL_COLORS[-1]
                        grid[row][col_idx] = (char, color)

        # Build the Rich Text object
        text = Text()
        for row_idx, row in enumerate(grid):
            for char, color in row:
                text.append(char, style=color)
            if row_idx < height - 1:
                text.append("\n")
        return text
