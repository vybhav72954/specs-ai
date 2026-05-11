<div align="center">
<pre>
███████╗██████╗ ███████╗ ██████╗███████╗       █████╗ ██╗
██╔════╝██╔══██╗██╔════╝██╔════╝██╔════╝      ██╔══██╗██║
███████╗██████╔╝█████╗  ██║     ███████╗█████╗███████║██║
╚════██║██╔═══╝ ██╔══╝  ██║     ╚════██║╚════╝██╔══██║██║
███████║██║     ███████╗╚██████╗███████║      ██║  ██║██║
╚══════╝╚═╝     ╚══════╝ ╚═════╝╚══════╝      ╚═╝  ╚═╝╚═╝
</pre>
</div>

<div align="center">

**AI-powered hardware upgrade assistant for Windows**

[![PyPI version](https://img.shields.io/pypi/v/specs-ai?color=3775A9&labelColor=0A0A0A&style=flat-square)](https://pypi.org/project/specs-ai/)
[![Python versions](https://img.shields.io/pypi/pyversions/specs-ai?color=3775A9&labelColor=0A0A0A&style=flat-square)](https://pypi.org/project/specs-ai/)
[![Downloads](https://img.shields.io/pypi/dm/specs-ai?color=F5A623&labelColor=0A0A0A&style=flat-square)](https://pypi.org/project/specs-ai/)
[![License](https://img.shields.io/pypi/l/specs-ai?color=00C853&labelColor=0A0A0A&style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D4?labelColor=0A0A0A&style=flat-square&logo=windows&logoColor=white)](https://pypi.org/project/specs-ai/)
[![Powered by Gemini](https://img.shields.io/badge/powered%20by-Gemini-8E75B2?labelColor=0A0A0A&style=flat-square&logo=googlegemini&logoColor=white)](https://aistudio.google.com/apikey)

</div>

---

`specs-ai` reads your machine's hardware via WMI and psutil, then asks a Gemini-powered LLM for specific, actionable upgrade recommendations — knowing exactly what you have.

**Collected specs:** CPU (model, cores, clock, socket), RAM (capacity, type, speed, slots), GPU (model, VRAM, Integrated/Dedicated), Motherboard, Storage (all drives, NVMe/SATA/HDD), WiFi adapter, Battery health (laptops), System uptime, OS metadata.

> The CPU socket tells the LLM whether a CPU is soldered (BGA — cannot upgrade) or swappable (LGA/AM4/etc.). GPU type tells it whether graphics are integrated (part of the CPU die, not upgradeable on a laptop) or a discrete card.

> [!WARNING]
> **Windows only.** `specs-ai` relies on WMI (Windows Management Instrumentation) and `pywin32` for hardware extraction. It will not run on Linux or macOS. There are no plans to support other platforms at this time.

---

## Screenshots

**Dashboard** (`specs-ai --dashboard`)

![Dashboard](https://raw.githubusercontent.com/vybhav72954/specs-ai/refs/heads/master/assets/dashboard.jpg)

**CLI Summary** (`specs-ai`)

![CLI Summary](https://raw.githubusercontent.com/vybhav72954/specs-ai/refs/heads/master/assets/summary.jpg)

**Detailed Recommendations** (`specs-ai --explain`)

![Explain Mode](https://raw.githubusercontent.com/vybhav72954/specs-ai/refs/heads/master/assets/explain.jpg)

---

## Install

```bash
pip install specs-ai
```

Or with [uv](https://docs.astral.sh/uv/):
```bash
uv pip install specs-ai
```

---

## API Key Setup

Get a free Gemini API key at https://aistudio.google.com/apikey, then pick one of:

**Option A — Shell environment variable:**
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
| *(none)* | Collect specs and show a compact upgrade summary table |
| `--explain` | Full detailed recommendations — specific part models, impact-per-dollar |
| `--specs-only` | Print hardware specs only; skip the LLM call entirely |
| `--dashboard` | Launch the interactive hacker-themed TUI dashboard |
| `--model MODEL` | Gemini model to use (default: `gemini-2.5-flash`) |

```powershell
# Compact summary table (default)
specs-ai

# Detailed recommendations with specific part suggestions
specs-ai --explain

# Interactive TUI dashboard
specs-ai --dashboard

# Just the hardware snapshot, no LLM call
specs-ai --specs-only
```

Also works via the module entry point:
```powershell
python -m specs_ai
python -m specs_ai --explain
python -m specs_ai --dashboard
```

---

## Dashboard

Launch with `specs-ai --dashboard` for a full-screen, hacker-themed hardware monitoring
dashboard built with [Textual](https://textual.textualize.io/) and [Rich](https://rich.readthedocs.io/).

**Features:**
- Big blocky ANSI Shadow `SPECS-AI` title in neon green
- Matrix-style digital rain animation on left/right gutters
- Live CPU sparkline, RAM usage bar, and per-volume disk usage bars
- Color-coded uptime — green < 5d, amber 5–15d, red > 15d
- AI upgrade recommendations panel (queries Gemini in the background)
- Scrolling event log with timestamped activity
- JSON export of the full hardware snapshot

| Key | Action |
|---|---|
| `Q` | Quit |
| `R` | Re-scan hardware + re-query Gemini |
| `E` | Toggle compact table / detailed explain mode |
| `S` | Export specs to `specs_report.json` |
| `H` | Toggle help overlay |

---

## How It Works

```
Your Machine
     │
     ▼
WMI + psutil          ← reads CPU, RAM, GPU, storage, battery, WiFi, uptime
     │
     ▼
Prompt builder        ← formats specs, injects BGA/iGPU/uptime advisories
     │
     ▼
Gemini API            ← gemini-2.5-flash by default; swap with --model
     │
     ▼
Upgrade recommendations (table or detailed narrative)
```

---

## Notes

- **BGA CPUs** (soldered) are correctly flagged as non-upgradeable
- **Integrated GPUs** on laptops are marked as non-upgradeable; on desktops, adding a discrete card is suggested
- **VRAM** is read from the Windows registry (not WMI) to avoid the 32-bit DWORD overflow that misreports GPUs with ≥ 4 GB VRAM
- **WMI calls** run in daemon threads with a 10-second timeout to prevent hangs on broken driver states
- **Uptime advisories** are injected into the prompt at 5 days (suggest reboot) and 15 days (strongly recommend reboot)

---

## Development

Requires [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/vybhav72954/specs-ai
cd specs-ai
uv run pytest tests/ -v
```

---

## Contributing & Issues

Bug reports and feature requests are welcome. If you run into a problem or have a suggestion, please [open an issue](https://github.com/vybhav72954/specs-ai/issues/new) on GitHub with:

- Your Windows version and Python version
- The full error message or unexpected output
- The command you ran

Pull requests are also welcome for bug fixes and improvements.

---

## License

[Apache 2.0](LICENSE)
