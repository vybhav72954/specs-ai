# specs-ai

AI-powered hardware upgrade assistant. Reads your machine's CPU, RAM, GPU, and motherboard specs via WMI and psutil, then asks a Gemini-powered LLM to give you specific, actionable upgrade recommendations for your exact hardware.

## Install

```
pip install specs-ai
```

## Usage

```
specs-ai
```

Set your Gemini API key before running:

```
$env:SPECS_AI_API_KEY = "your-key-here"
```
