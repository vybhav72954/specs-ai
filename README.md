# specs-ai

AI-powered hardware upgrade assistant. Reads your machine's CPU, RAM, GPU, motherboard,
storage, WiFi adapter, and battery health (on laptops) via WMI and psutil, then asks a
Gemini-powered LLM to give you specific, actionable upgrade recommendations for your
exact hardware.

Currently Windows-only.

## Install

```
pip install specs-ai
```

## API key setup

Get a free Gemini API key at https://aistudio.google.com/apikey, then pick one of:

**Option A — shell environment variable:**
```
$env:SPECS_AI_API_KEY = "your-key-here"
```

**Option B — `.env` file** (in the project root or any parent directory):
```
SPECS_AI_API_KEY=your-key-here
```

A template is provided at `.env.example` — copy it to `.env` and fill in your key.

## Usage

```
specs-ai
```

Or, equivalently:
```
python -m specs_ai
```
