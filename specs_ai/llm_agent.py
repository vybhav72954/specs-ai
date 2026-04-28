"""LLM prompt construction and API calls."""

import os
from typing import Any

from dotenv import load_dotenv
from google import genai

_DEFAULT_MODEL = "gemini-2.5-flash"

# Values that mean "user didn't actually configure a key" — typically left over
# from copying .env.example without editing.
_PLACEHOLDER_KEYS: frozenset[str] = frozenset(
    {
        "your-gemini-api-key-here",
        "your-key-here",
        "your-key",
        "your-api-key",
        "changeme",
    }
)


def _load_api_key() -> str:
    """Return SPECS_AI_API_KEY from environment, falling back to a .env file.

    Raises EnvironmentError with setup instructions if the key is absent or
    still contains the .env.example placeholder.
    """
    key = os.getenv("SPECS_AI_API_KEY")
    if not key:
        load_dotenv()  # searches cwd and all parent directories
        key = os.getenv("SPECS_AI_API_KEY")

    cleaned = (key or "").strip()
    if not cleaned or cleaned.lower() in _PLACEHOLDER_KEYS:
        raise EnvironmentError(
            "SPECS_AI_API_KEY is not set or still contains the placeholder value.\n"
            "  Option 1 — shell:    $env:SPECS_AI_API_KEY = 'your-key'\n"
            "  Option 2 — .env file: add  SPECS_AI_API_KEY=your-key  to a .env file\n"
            "                         in the project root or any parent directory.\n"
            "Get a key at: https://aistudio.google.com/apikey"
        )
    return cleaned


def _format_value(value: Any, suffix: str = "") -> str:
    """Render a spec value for the prompt, hiding noisy float decimals."""
    if value is None or value == "Unknown":
        return "Unknown"
    if isinstance(value, float) and value.is_integer():
        return f"{int(value)}{suffix}"
    return f"{value}{suffix}"


def _build_prompt(specs: dict[str, Any]) -> str:
    """Format a HardwareSpecs-shaped dict into an upgrade-recommendation prompt."""
    cpu = specs.get("cpu") or {}
    ram = specs.get("ram") or {}
    gpu = specs.get("gpu") or {}
    mb = specs.get("motherboard") or {}

    ram_type = ram.get("ram_type") or ""
    ram_type_part = f"{ram_type} " if ram_type and ram_type != "Unknown" else ""

    sys_model = mb.get("system_model", "Unknown")
    sys_model_part = f" [{sys_model}]" if sys_model and sys_model != "Unknown" else ""

    specs_block = (
        f"CPU:         {cpu.get('name', 'Unknown')} "
        f"({_format_value(cpu.get('physical_cores', '?'))}c / "
        f"{_format_value(cpu.get('logical_cores', '?'))}t, "
        f"max {_format_value(cpu.get('max_clock_mhz', '?'))} MHz)\n"
        f"RAM:         {_format_value(ram.get('total_gb', '?'))} GB "
        f"{ram_type_part}@ {_format_value(ram.get('speed_mhz', '?'))} MHz "
        f"- {_format_value(ram.get('slots_used', '?'))} slot(s) used\n"
        f"GPU:         {gpu.get('name', 'Unknown')} "
        f"({_format_value(gpu.get('vram_gb', '?'))} GB VRAM)\n"
        f"Motherboard: {mb.get('manufacturer', 'Unknown')} {mb.get('model', 'Unknown')}{sys_model_part}"
    )

    return (
        "You are an expert PC hardware technician.\n"
        "The user wants upgrade recommendations for their exact machine.\n"
        "Be specific: name actual part models and explain the real-world benefit "
        "of each upgrade. Prioritise by impact-per-dollar. Be concise.\n\n"
        "Known specs (this is the complete set of components retrieved from the machine):\n"
        "---\n"
        f"{specs_block}\n"
        "---\n\n"
        "IMPORTANT: Only recommend upgrades for the components listed above "
        "(CPU, RAM, GPU, Motherboard). "
        "Do NOT mention, assume, or speculate about components that are not listed "
        "(e.g. storage, PSU, cooling, peripherals). "
        "If you have no meaningful upgrade recommendation for a listed component, skip it.\n\n"
        "What are the best upgrade paths for the components listed above?"
    )


def get_recommendations(specs: dict[str, Any], model: str = _DEFAULT_MODEL) -> str:
    """Build a prompt from specs and return Gemini's upgrade recommendations.

    Args:
        specs: Hardware specs as a plain dict (use dataclasses.asdict on HardwareSpecs).
        model: Gemini model ID to use (default: gemini-2.5-flash).

    Returns:
        Recommendation text from the model.

    Raises:
        EnvironmentError: If SPECS_AI_API_KEY is not configured.
        RuntimeError:     If the Gemini API call fails (network, auth, quota, etc.).
    """
    api_key = _load_api_key()
    prompt = _build_prompt(specs)
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model, contents=prompt)
    except Exception as e:
        raise RuntimeError(f"Gemini API call failed ({type(e).__name__}): {e}") from e

    text = getattr(response, "text", None)
    return text if text else "No recommendations returned by the model."
