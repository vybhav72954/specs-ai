"""LLM prompt construction and API calls."""

import os
from typing import Any

from dotenv import load_dotenv
from google import genai

DEFAULT_MODEL = "gemini-2.5-flash"

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


def _build_prompt(specs: dict[str, Any], verbose: bool = False) -> str:
    """Format a HardwareSpecs-shaped dict into an upgrade-recommendation prompt.

    Args:
        specs:   Hardware specs dict (from dataclasses.asdict on HardwareSpecs).
        verbose: True → detailed narrative with part names and impact-per-dollar.
                 False (default) → compact markdown summary table.
    """
    cpu = specs.get("cpu") or {}
    ram = specs.get("ram") or {}
    gpu = specs.get("gpu") or {}
    mb = specs.get("motherboard") or {}
    wifi = specs.get("wifi") or {}
    system = specs.get("system") or {}

    ram_type = ram.get("ram_type") or ""
    ram_type_part = f"{ram_type} " if ram_type and ram_type != "Unknown" else ""

    sys_model = mb.get("system_model", "Unknown")
    sys_model_part = f" [{sys_model}]" if sys_model and sys_model != "Unknown" else ""

    drives = specs.get("drives") or []
    if drives:
        drive_strs = [
            f"{d.get('name', 'Unknown')} "
            f"({_format_value(d.get('size_gb', '?'))} GB, {d.get('drive_type', 'Unknown')})"
            for d in drives
        ]
        if len(drive_strs) == 1:
            storage_line = f"Storage:     {drive_strs[0]}"
        else:
            continuation = "\n             "
            storage_line = "Storage:     " + continuation.join(drive_strs)
    else:
        storage_line = "Storage:     Unknown"

    wifi_name = wifi.get("name", "Unknown")

    power = specs.get("power") or {}
    has_battery = bool(power.get("has_battery", False))
    if has_battery:
        bat_name = power.get("battery_name", "Unknown") or "Unknown"
        health_raw = power.get("health_pct", "Unknown")
        health_str = f"{_format_value(health_raw)}%" if health_raw != "Unknown" else "Unknown"
        design = power.get("design_capacity_mwh", "Unknown")
        full_chg = power.get("full_charge_capacity_mwh", "Unknown")
        if design != "Unknown" and full_chg != "Unknown":
            cap_str = (
                f",  Design: {_format_value(design)} mWh,"
                f"  Current max: {_format_value(full_chg)} mWh"
            )
        else:
            cap_str = ""
        battery_line = f"\nBattery:     {bat_name}  (Health: {health_str}{cap_str})"
        listed_components = "(CPU, RAM, GPU, Motherboard, Storage, WiFi, Battery)"
        battery_note = (
            "NOTE: If recommending a battery replacement for a laptop, always warn the user "
            "that sourcing genuine OEM replacement batteries can be difficult as original parts "
            "are often not readily available; advise using a certified service centre or a "
            "carefully vetted third-party supplier.\n\n"
        )
    else:
        battery_line = "\nNote:        Desktop - PSU and battery info not available via WMI."
        listed_components = "(CPU, RAM, GPU, Motherboard, Storage, WiFi)"
        battery_note = "\n"

    os_name = system.get("os_name", "Unknown")
    os_build = system.get("os_build", "Unknown")
    os_install_date = system.get("os_install_date", "Unknown")
    system_type = system.get("system_type", "Unknown")
    uptime_seconds = system.get("uptime_seconds", "Unknown")

    if isinstance(uptime_seconds, int):
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        uptime_str = f"{days}d {hours}h"
    else:
        uptime_str = "Unknown"

    system_line = (
        f"OS:          {os_name} (build {os_build})\n"
        f"System:      {system_type}  |  OS installed: {os_install_date}"
        " (install date, not necessarily purchase date)\n"
        f"Uptime:      {uptime_str}"
    )

    # Uptime advisory — thresholds: < 5d normal, 5-15d suggest reboot, > 15d strongly recommend.
    if isinstance(uptime_seconds, int) and uptime_seconds >= 5 * 86400:
        if uptime_seconds >= 15 * 86400:
            uptime_note = (
                "NOTE: System uptime exceeds 15 days. Strongly recommend the user reboot "
                "to apply pending OS and driver updates, flush accumulated memory leaks, "
                "and restore system stability. This should be flagged as a high-priority "
                "recommendation.\n"
            )
        else:
            uptime_note = (
                "NOTE: System uptime exceeds 5 days. Advise the user to reboot periodically "
                "to apply pending OS and driver updates and maintain system stability.\n"
            )
    else:
        uptime_note = ""

    specs_block = (
        f"{system_line}\n"
        f"CPU:         {cpu.get('name', 'Unknown')} "
        f"({_format_value(cpu.get('physical_cores', '?'))}c / "
        f"{_format_value(cpu.get('logical_cores', '?'))}t, "
        f"max {_format_value(cpu.get('max_clock_mhz', '?'))} MHz, "
        f"socket: {cpu.get('socket', 'Unknown')})\n"
        f"RAM:         {_format_value(ram.get('total_gb', '?'))} GB "
        f"{ram_type_part}@ {_format_value(ram.get('speed_mhz', '?'))} MHz "
        f"- {_format_value(ram.get('slots_used', '?'))} slot(s) used\n"
        f"GPU:         {gpu.get('name', 'Unknown')} "
        f"({_format_value(gpu.get('vram_gb', '?'))} GB VRAM, "
        f"{gpu.get('gpu_type', 'Unknown')})\n"
        f"Motherboard: {mb.get('manufacturer', 'Unknown')} {mb.get('model', 'Unknown')}{sys_model_part}\n"
        f"{storage_line}\n"
        f"WiFi:        {wifi_name}"
        f"{battery_line}"
    )

    # Advisory note shared by both prompt modes.
    hardware_note = (
        "NOTE: If the CPU socket starts with 'BGA', the CPU is soldered to the board "
        "and cannot be replaced - Status: Cannot upgrade. "
        "If the GPU type is 'Integrated', it is part of the CPU die and cannot be upgraded "
        "separately; on a desktop you may suggest adding a discrete GPU, but on a laptop "
        "this is not possible.\n"
    )

    if not verbose:
        return (
            "You are an expert PC hardware technician.\n"
            "The user wants a quick upgrade summary for their machine.\n"
            "Respond with a markdown table with three columns: Component | Status | Notes\n"
            "Status must be exactly one of: Cannot upgrade | Upgradeable | Up to date | Monitor\n"
            "Notes: 1-2 sentences. For Cannot upgrade: state why (e.g. BGA socket, soldered RAM). "
            "For Upgradeable: name the specific upgrade target and its main benefit.\n\n"
            "Known specs (complete set of components retrieved from the machine):\n"
            "---\n"
            f"{specs_block}\n"
            "---\n\n"
            f"IMPORTANT: Only include in the table the components listed above "
            f"{listed_components}. "
            "Do NOT mention, assume, or speculate about components that are not listed "
            "(e.g. PSU, cooling, peripherals).\n"
            f"{hardware_note}"
            f"{uptime_note}"
            f"{battery_note}"
            "After the table, add exactly this line:\n"
            "Run `specs-ai --explain` for detailed part recommendations and impact analysis."
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
        f"IMPORTANT: Only recommend upgrades for the components listed above "
        f"{listed_components}. "
        "Do NOT mention, assume, or speculate about components that are not listed "
        "(e.g. PSU, cooling, peripherals). "
        "If you have no meaningful upgrade recommendation for a listed component, skip it.\n"
        f"{hardware_note}"
        f"{uptime_note}"
        f"{battery_note}"
        "What are the best upgrade paths for the components listed above?"
    )


def get_recommendations(
    specs: dict[str, Any],
    model: str = DEFAULT_MODEL,
    verbose: bool = False,
) -> str:
    """Build a prompt from specs and return Gemini's upgrade recommendations.

    Args:
        specs:   Hardware specs as a plain dict (use dataclasses.asdict on HardwareSpecs).
        model:   Gemini model ID to use (default: gemini-2.5-flash).
        verbose: True → detailed narrative with part names and impact-per-dollar.
                 False (default) → compact markdown summary table.

    Returns:
        Recommendation text from the model.

    Raises:
        EnvironmentError: If SPECS_AI_API_KEY is not configured.
        RuntimeError:     If the Gemini API call fails (network, auth, quota, etc.).
    """
    api_key = _load_api_key()
    prompt = _build_prompt(specs, verbose=verbose)
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model, contents=prompt)
    except Exception as e:
        raise RuntimeError(f"Gemini API call failed ({type(e).__name__}): {e}") from e

    text = getattr(response, "text", None)
    return text if text else "No recommendations returned by the model."
