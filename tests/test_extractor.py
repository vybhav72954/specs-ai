"""Tests for extractor.py."""

from specs_ai.extractor import (
    CPUInfo,
    GPUInfo,
    HardwareSpecs,
    MotherboardInfo,
    PowerInfo,
    RAMInfo,
    StorageInfo,
    SystemInfo,
    WiFiInfo,
    _adapter_ram_to_bytes,
    _clean_board_string,
    _is_integrated_gpu,
    _is_real_gpu,
    _is_real_wifi,
    _MEMORY_TYPE_MAP,
    _parse_wmi_date,
    collect,
)


# ---- integration: live WMI on this machine ----------------------------------


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
    assert isinstance(cpu.max_clock_mhz, (int, str))
    assert isinstance(cpu.socket, str) and cpu.socket != ""


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
    assert gpu.gpu_type in ("Integrated", "Dedicated", "Unknown")
    assert gpu.gpu_type != ""


def test_motherboard_fields() -> None:
    """Motherboard fields must be their declared type or the string 'Unknown'."""
    mb = collect().motherboard
    assert isinstance(mb, MotherboardInfo)
    assert isinstance(mb.manufacturer, str)
    assert isinstance(mb.model, str)
    assert isinstance(mb.system_model, str)


def test_no_empty_strings() -> None:
    """No string field should be empty — must be a value or 'Unknown'."""
    specs = collect()
    assert specs.cpu.name != ""
    assert specs.gpu.name != ""
    assert specs.motherboard.manufacturer != ""
    assert specs.motherboard.model != ""
    assert specs.motherboard.system_model != ""
    assert specs.ram.ram_type != ""
    assert specs.power.battery_name != ""


# ---- unit: pure helpers ------------------------------------------------------


def test_adapter_ram_handles_negative_signed_int32() -> None:
    """pywin32 surfaces uint32 as signed; -1048576 must become 4293918720."""
    assert _adapter_ram_to_bytes(-1048576) == 4293918720
    assert _adapter_ram_to_bytes(-2147483648) == 2147483648


def test_adapter_ram_handles_none_and_garbage() -> None:
    """Non-numeric or None input must coerce to 0 without raising."""
    assert _adapter_ram_to_bytes(None) == 0
    assert _adapter_ram_to_bytes("not a number") == 0
    assert _adapter_ram_to_bytes(0) == 0


def test_adapter_ram_passes_through_positive() -> None:
    """Positive values pass through unchanged."""
    assert _adapter_ram_to_bytes(2_000_000_000) == 2_000_000_000


def test_is_real_gpu_filters_virtual_adapters() -> None:
    """Virtual / fallback display adapters must be rejected."""
    assert not _is_real_gpu("Microsoft Basic Display Adapter")
    assert not _is_real_gpu("Microsoft Remote Display Adapter")
    assert not _is_real_gpu("Citrix Indirect Display Adapter")
    assert not _is_real_gpu("VMware SVGA 3D")
    assert not _is_real_gpu("VirtualBox Graphics Adapter")
    assert not _is_real_gpu(None)
    assert not _is_real_gpu("")


def test_is_real_gpu_accepts_real_hardware() -> None:
    """Real GPU names must pass through."""
    assert _is_real_gpu("NVIDIA GeForce GTX 1650")
    assert _is_real_gpu("AMD Radeon RX 6800 XT")
    assert _is_real_gpu("Intel(R) UHD Graphics 630")


def test_clean_board_string_filters_placeholders() -> None:
    """Common BIOS placeholder strings must collapse to 'Unknown'."""
    assert _clean_board_string("To Be Filled By O.E.M.") == "Unknown"
    assert _clean_board_string("Default string") == "Unknown"
    assert _clean_board_string("System manufacturer") == "Unknown"
    assert _clean_board_string("System Product Name") == "Unknown"
    assert _clean_board_string("Not Specified") == "Unknown"
    assert _clean_board_string("N/A") == "Unknown"
    assert _clean_board_string("") == "Unknown"
    assert _clean_board_string(None) == "Unknown"
    assert _clean_board_string("   ") == "Unknown"


def test_clean_board_string_preserves_real_values() -> None:
    """Real manufacturer / model strings must be returned, only stripped."""
    assert _clean_board_string("ASUSTeK COMPUTER INC.") == "ASUSTeK COMPUTER INC."
    assert _clean_board_string("  FX505DT  ") == "FX505DT"


def test_memory_type_map_covers_common_generations() -> None:
    """The DDR generation map must include modern types the LLM cares about."""
    assert _MEMORY_TYPE_MAP[24] == "DDR3"
    assert _MEMORY_TYPE_MAP[26] == "DDR4"
    assert _MEMORY_TYPE_MAP[34] == "DDR5"


def test_drives_is_list() -> None:
    """drives must always be a list — never None or absent."""
    drives = collect().drives
    assert isinstance(drives, list)


def test_drives_fields() -> None:
    """Each StorageInfo entry must have the expected field types and no empty strings."""
    for drive in collect().drives:
        assert isinstance(drive, StorageInfo)
        assert isinstance(drive.name, str)
        assert isinstance(drive.size_gb, (float, str))
        assert isinstance(drive.drive_type, str)
        assert drive.name != ""
        assert drive.drive_type != ""


def test_wifi_fields() -> None:
    """WiFiInfo must always be present with a non-empty string name."""
    wifi = collect().wifi
    assert isinstance(wifi, WiFiInfo)
    assert isinstance(wifi.name, str)
    assert wifi.name != ""


def test_system_fields() -> None:
    """SystemInfo must always be present with non-empty string fields."""
    system = collect().system
    assert isinstance(system, SystemInfo)
    assert isinstance(system.os_name, str) and system.os_name != ""
    assert isinstance(system.os_version, str) and system.os_version != ""
    assert isinstance(system.os_build, str) and system.os_build != ""
    assert isinstance(system.os_install_date, str) and system.os_install_date != ""
    assert isinstance(system.system_type, str) and system.system_type != ""


def test_power_fields() -> None:
    """PowerInfo must always be present with correct field types."""
    power = collect().power
    assert isinstance(power, PowerInfo)
    assert isinstance(power.battery_name, str)
    assert isinstance(power.has_battery, bool)
    assert isinstance(power.design_capacity_mwh, (int, str))
    assert isinstance(power.full_charge_capacity_mwh, (int, str))
    assert isinstance(power.health_pct, (int, str))
    assert power.battery_name != ""
    if power.has_battery and isinstance(power.health_pct, int):
        assert 0 <= power.health_pct <= 200  # sanity bound; >100 possible on new batteries


# ---- unit: WiFi helpers -------------------------------------------------------


def test_is_real_wifi_accepts_wifi_adapters() -> None:
    """Common WiFi adapter names and types must be accepted."""
    assert _is_real_wifi("Intel(R) Wi-Fi 6 AX200 160MHz", None)
    assert _is_real_wifi("Realtek RTL8822CE Wireless LAN 802.11ac PCI-E NIC", None)
    assert _is_real_wifi("Qualcomm Atheros QCA9377 Wireless Network Adapter", None)
    assert _is_real_wifi("Some Adapter", "Ethernet 802.11")


def test_is_real_wifi_rejects_virtual_adapters() -> None:
    """Virtual and Bluetooth adapters must be rejected."""
    assert not _is_real_wifi("Microsoft Wi-Fi Direct Virtual Adapter", None)
    assert not _is_real_wifi("Microsoft Hosted Network Virtual Adapter", None)
    assert not _is_real_wifi("Bluetooth Device (Personal Area Network)", None)
    assert not _is_real_wifi(None, None)
    assert not _is_real_wifi("", None)


def test_is_real_wifi_rejects_wired_adapters() -> None:
    """Wired Ethernet adapters must not be treated as WiFi."""
    assert not _is_real_wifi("Realtek PCIe GbE Family Controller", None)
    assert not _is_real_wifi("Intel(R) Ethernet Connection I219-V", "Ethernet 802.3")


# ---- unit: _is_integrated_gpu -----------------------------------------------


def test_is_integrated_gpu_accepts_known_igpu() -> None:
    """Common integrated GPU names must be recognised."""
    assert _is_integrated_gpu("Intel(R) UHD Graphics 630")
    assert _is_integrated_gpu("Intel(R) HD Graphics 520")
    assert _is_integrated_gpu("Intel(R) Iris(R) Xe Graphics")
    assert _is_integrated_gpu("AMD Radeon Graphics")


def test_is_integrated_gpu_rejects_discrete() -> None:
    """Discrete GPU names must not be classified as integrated."""
    assert not _is_integrated_gpu("NVIDIA GeForce GTX 1650")
    assert not _is_integrated_gpu("AMD Radeon RX 6800 XT")
    assert not _is_integrated_gpu("AMD Radeon Pro 5500M")


def test_is_integrated_gpu_rejects_empty_and_none() -> None:
    """None and empty string must return False without raising."""
    assert not _is_integrated_gpu(None)
    assert not _is_integrated_gpu("")


# ---- unit: _parse_wmi_date ---------------------------------------------------


def test_parse_wmi_date_valid_dmtf() -> None:
    """Full DMTF datetime string must parse to YYYY-MM-DD."""
    assert _parse_wmi_date("20230514152345.123456+000") == "2023-05-14"


def test_parse_wmi_date_date_only_prefix() -> None:
    """Bare 8-digit date prefix is enough to produce a valid result."""
    assert _parse_wmi_date("20230101") == "2023-01-01"


def test_parse_wmi_date_none_returns_unknown() -> None:
    """None input must return 'Unknown'."""
    assert _parse_wmi_date(None) == "Unknown"


def test_parse_wmi_date_short_string_returns_unknown() -> None:
    """Strings shorter than 8 characters must return 'Unknown'."""
    assert _parse_wmi_date("2023") == "Unknown"
    assert _parse_wmi_date("") == "Unknown"
