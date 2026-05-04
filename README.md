# specs-ai

AI-powered hardware upgrade assistant for Windows. Reads your machine's hardware via
WMI and psutil, then asks a Gemini-powered LLM for specific, actionable upgrade
recommendations — knowing exactly what you have.

**Collected specs:** CPU (model, cores, clock, socket), RAM (capacity, type, speed,
slots), GPU (model, VRAM, Integrated/Dedicated), Motherboard, Storage (all drives,
NVMe/SATA/HDD), WiFi adapter, Battery health (laptops), System uptime, OS metadata.

The CPU socket lets the LLM know whether the CPU is soldered (BGA — cannot upgrade)
or swappable (LGA/AM4/etc.). GPU type tells it whether the graphics are integrated
(part of the CPU die) or a discrete card.

Currently Windows-only.

---

## Install

```
pip install specs-ai
```

Or with [uv](https://docs.astral.sh/uv/):
```
uv pip install specs-ai
```

---

## API key setup

Get a free Gemini API key at https://aistudio.google.com/apikey, then pick one of:

**Option A — shell environment variable:**
```powershell
$env:SPECS_AI_API_KEY = "your-key-here"
```

**Option B — `.env` file** (in the project root or any parent directory):
```
SPECS_AI_API_KEY=your-key-here
```

A template is provided at `.env.example` — copy it to `.env` and fill in your key.

---

## Usage

```
specs-ai [--explain] [--specs-only] [--dashboard] [--model MODEL]
```

| Flag | Description |
|---|---|
| *(none)* | Collect specs and show a compact summary table of upgrade options |
| `--explain` | Full detailed recommendations — specific part models, impact-per-dollar |
| `--specs-only` | Print hardware specs only; skip the LLM call entirely |
| `--dashboard` | Launch the interactive hacker-esque TUI dashboard |
| `--model MODEL` | Gemini model to use (default: `gemini-2.5-flash`) |

**Quick start:**
```powershell
# Summary table (default)
specs-ai

# Detailed recommendations
specs-ai --explain

# Interactive TUI dashboard
specs-ai --dashboard

# Just the hardware specs, no LLM
specs-ai --specs-only
```

Or equivalently via the module entry point:
```powershell
python -m specs_ai
python -m specs_ai --explain
python -m specs_ai --dashboard
```

---

## TUI Dashboard

Launch with `specs-ai --dashboard` for a full-screen, hacker-themed hardware monitoring
dashboard built with [Textual](https://textual.textualize.io/) and
[Rich](https://rich.readthedocs.io/).

**Features:**
- Big blocky ANSI Shadow "SPECS-AI" title in neon green
- Matrix-style digital rain animation on left/right gutters
- Live CPU sparkline, RAM usage bar, and disk usage bars
- Color-coded uptime (green < 5d, amber 5-15d, red > 15d)
- AI upgrade recommendations panel (queries Gemini in background)
- Scrolling event log with timestamped activity
- Keybindings: `[Q]` Quit, `[R]` Re-scan, `[E]` Toggle explain, `[S]` Export, `[?]` Help

---

For development and testing (requires [uv](https://docs.astral.sh/uv/)):
```bash
uv run pytest tests/ -v
```