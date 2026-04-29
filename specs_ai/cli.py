"""CLI entry point for specs-ai."""

import argparse
import dataclasses
import sys

from specs_ai import __version__
from specs_ai.extractor import HardwareSpecs, collect
from specs_ai.llm_agent import DEFAULT_MODEL, get_recommendations


def _fmt(value: object, suffix: str = "") -> str:
    """Format a spec value for display, dropping '.0' from whole-number floats."""
    if value is None or value == "Unknown":
        return "Unknown"
    if isinstance(value, float) and value.is_integer():
        return f"{int(value)}{suffix}"
    return f"{value}{suffix}"


def _print_specs(specs: HardwareSpecs) -> None:
    """Print a formatted hardware spec table to stdout."""
    cpu = specs.cpu
    ram = specs.ram
    gpu = specs.gpu
    mb = specs.motherboard

    ram_type = f"{ram.ram_type} " if ram.ram_type and ram.ram_type != "Unknown" else ""

    print("Hardware specs")
    print("-" * 44)
    print(f"CPU:         {cpu.name}")
    print(f"             {_fmt(cpu.physical_cores)}c / {_fmt(cpu.logical_cores)}t"
          f"  max {_fmt(cpu.max_clock_mhz)} MHz")
    print(f"RAM:         {_fmt(ram.total_gb)} GB {ram_type}"
          f"@ {_fmt(ram.speed_mhz)} MHz  ({_fmt(ram.slots_used)} slot(s))")
    print(f"GPU:         {gpu.name}  ({_fmt(gpu.vram_gb)} GB VRAM)")
    sys_model = f"  [{mb.system_model}]" if mb.system_model and mb.system_model != "Unknown" else ""
    print(f"Motherboard: {mb.manufacturer} {mb.model}{sys_model}")
    if specs.drives:
        if len(specs.drives) == 1:
            d = specs.drives[0]
            print(f"Storage:     {d.name}  ({_fmt(d.size_gb)} GB, {d.drive_type})")
        else:
            print(f"Storage ({len(specs.drives)}):")
            for d in specs.drives:
                print(f"             {d.name}  ({_fmt(d.size_gb)} GB, {d.drive_type})")
    else:
        print("Storage:     Unknown")
    print(f"WiFi:        {specs.wifi.name}")
    p = specs.power
    if p.has_battery:
        health_str = f"{_fmt(p.health_pct)}%" if p.health_pct != "Unknown" else "Unknown"
        if p.design_capacity_mwh != "Unknown" and p.full_charge_capacity_mwh != "Unknown":
            cap_str = (
                f",  {_fmt(p.design_capacity_mwh)} mWh design"
                f" -> {_fmt(p.full_charge_capacity_mwh)} mWh max"
            )
        else:
            cap_str = ""
        print(f"Battery:     {p.battery_name}  (Health: {health_str}{cap_str})")
    else:
        print("Note:        Desktop - PSU and battery info not available via WMI.")
    print("-" * 44)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Build the argument parser and return parsed args."""
    parser = argparse.ArgumentParser(
        prog="specs-ai",
        description="Collect hardware specs and get AI-powered upgrade recommendations.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"specs-ai {__version__}",
    )
    parser.add_argument(
        "--specs-only",
        action="store_true",
        help="Print hardware specs without calling the LLM.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        metavar="MODEL",
        help=f"Gemini model ID to use (default: {DEFAULT_MODEL}).",
    )
    return parser.parse_args(argv)


def main() -> None:
    """Run the specs-ai CLI: collect specs, optionally query Gemini for recommendations."""
    args = _parse_args()

    print("Collecting hardware specs...", flush=True)
    specs = collect()
    print()
    _print_specs(specs)

    if args.specs_only:
        return

    print()
    print("Querying Gemini for upgrade recommendations...", flush=True)
    print()
    try:
        recommendations = get_recommendations(dataclasses.asdict(specs), model=args.model)
    except EnvironmentError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(recommendations)
