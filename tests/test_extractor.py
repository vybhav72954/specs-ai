"""Tests for extractor.py."""

from specs_ai.extractor import (
    CPUInfo,
    GPUInfo,
    HardwareSpecs,
    MotherboardInfo,
    RAMInfo,
    collect,
)


def test_collect_returns_hardware_specs() -> None:
    """collect() must always return a HardwareSpecs instance without raising."""
    specs = collect()
    assert isinstance(specs, HardwareSpecs)


def test_cpu_fields() -> None:
    """CPU fields must be their declared type or the string 'Unknown'."""
    cpu = collect().cpu
    assert isinstance(cpu, CPUInfo)
    assert isinstance(cpu.name, str)
    assert isinstance(cpu.physical_cores, (int, str))
    assert isinstance(cpu.logical_cores, (int, str))
    assert isinstance(cpu.max_clock_mhz, (float, str))


def test_ram_fields() -> None:
    """RAM fields must be their declared type or the string 'Unknown'."""
    ram = collect().ram
    assert isinstance(ram, RAMInfo)
    assert isinstance(ram.total_gb, (float, str))
    assert isinstance(ram.slots_used, (int, str))
    assert isinstance(ram.speed_mhz, (int, str))
    assert isinstance(ram.ram_type, str)


def test_gpu_fields() -> None:
    """GPU fields must be their declared type or the string 'Unknown'."""
    gpu = collect().gpu
    assert isinstance(gpu, GPUInfo)
    assert isinstance(gpu.name, str)
    assert isinstance(gpu.vram_gb, (float, str))


def test_motherboard_fields() -> None:
    """Motherboard fields must be their declared type or the string 'Unknown'."""
    mb = collect().motherboard
    assert isinstance(mb, MotherboardInfo)
    assert isinstance(mb.manufacturer, str)
    assert isinstance(mb.model, str)


def test_no_empty_strings() -> None:
    """No string field should be empty — must be a value or 'Unknown'."""
    specs = collect()
    assert specs.cpu.name != ""
    assert specs.gpu.name != ""
    assert specs.motherboard.manufacturer != ""
    assert specs.motherboard.model != ""
    assert specs.ram.ram_type != ""
