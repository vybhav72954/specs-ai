"""Matrix digital rain gutter columns."""

import random

from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip
from textual.widget import Widget


# Character pool: katakana range, ASCII digits, Latin uppercase, symbols
_CHAR_POOL: tuple[str, ...] = tuple(
    [chr(c) for c in range(0x30A0, 0x30FF + 1)]
    + list("0123456789")
    + list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    + list("@#$%&*")
)

_BG_COLOR = "#0A0A0A"
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

# Pre-built Style objects — avoids Style.parse() on every character every tick.
_BG_STYLE = Style(color=_BG_COLOR)
_HEAD_STYLE = Style(color=_HEAD_COLOR, bold=True)
_TRAIL_STYLES: list[Style] = [Style(color=c) for c in _TRAIL_COLORS]
_TAIL_STYLE = _TRAIL_STYLES[-1]


def _stream_style(i: int) -> Style:
    """Return the pre-built Style for position i in a stream (0 = head)."""
    if i == 0:
        return _HEAD_STYLE
    return _TRAIL_STYLES[i - 1] if i - 1 < len(_TRAIL_STYLES) else _TAIL_STYLE


_BG_CELL = (" ", _BG_STYLE)

_STREAMS_PER_COLUMN = 3


class _Stream:
    """A single falling column of characters."""

    __slots__ = ("height", "length", "head", "chars", "delay")

    def __init__(self, height: int) -> None:
        self.height = height
        self.length = random.randint(6, 14)
        self.head = random.randint(-self.length, height // 3)
        self.chars: list[str] = [random.choice(_CHAR_POOL) for _ in range(self.length)]
        self.delay = 0

    def advance(self) -> None:
        """Move the stream down one row."""
        if self.delay > 0:
            self.delay -= 1
            return
        self.head += 1
        self.chars[0] = random.choice(_CHAR_POOL)
        if self.head - self.length > self.height:
            self._reset()

    def _reset(self) -> None:
        self.head = random.randint(-self.length, 0)
        self.length = random.randint(6, 14)
        self.chars = [random.choice(_CHAR_POOL) for _ in range(self.length)]
        self.delay = random.randint(0, 8)


class MatrixRain(Widget):
    """A narrow column of falling Matrix-style characters."""

    DEFAULT_CSS = """
    MatrixRain {
        width: 2;
        height: 100%;
        background: #0A0A0A;
    }
    """

    def __init__(self, columns: int = 2, **kwargs) -> None:
        super().__init__(**kwargs)
        self._columns = columns
        self._streams: list[list[_Stream]] = []
        # Grid pre-computed in _tick(); render_line() just reads from it.
        # _grid[row][col] = (char, Style)
        self._grid: list[list[tuple[str, Style]]] = []

    def _make_streams(self, height: int) -> list[list[_Stream]]:
        return [
            [_Stream(height) for _ in range(_STREAMS_PER_COLUMN)]
            for _ in range(self._columns)
        ]

    def _rebuild_grid(self, height: int) -> None:
        """Recompute every cell from current stream positions."""
        grid: list[list[tuple[str, Style]]] = [
            [_BG_CELL] * self._columns for _ in range(height)
        ]
        for col_idx, col_streams in enumerate(self._streams):
            for stream in col_streams:
                for i in range(stream.length):
                    row = stream.head - i
                    if 0 <= row < height:
                        grid[row][col_idx] = (
                            stream.chars[i % len(stream.chars)],
                            _stream_style(i),
                        )
        self._grid = grid

    def on_mount(self) -> None:
        height = self.size.height or 30
        self._streams = self._make_streams(height)
        self._rebuild_grid(height)
        self.set_interval(1 / 8, self._tick)

    def on_resize(self) -> None:
        height = self.size.height or 30
        self._streams = self._make_streams(height)
        self._rebuild_grid(height)

    def _tick(self) -> None:
        """Advance streams, pre-compute grid, then schedule a single refresh."""
        height = self.size.height or 30
        for col_streams in self._streams:
            for stream in col_streams:
                stream.advance()
        self._rebuild_grid(height)
        self.refresh()

    def render_line(self, y: int) -> Strip:
        """Render one row — called by Textual for each visible line."""
        if not self._grid or y >= len(self._grid):
            return Strip([Segment(" " * self._columns, _BG_STYLE)])
        return Strip([Segment(char, style) for char, style in self._grid[y]])
