"""Tests for cli.py."""

from unittest.mock import patch

import pytest

from specs_ai.cli import _fmt, _parse_args, _print_specs, main
from specs_ai.extractor import CPUInfo, GPUInfo, HardwareSpecs, MotherboardInfo, PowerInfo, RAMInfo, StorageInfo, SystemInfo, WiFiInfo
from specs_ai.llm_agent import DEFAULT_MODEL


# ---- fixtures ----------------------------------------------------------------


@pytest.fixture
def sample_specs() -> HardwareSpecs:
    """Realistic HardwareSpecs snapshot used across multiple tests."""
    return HardwareSpecs(
        cpu=CPUInfo(name="AMD Ryzen 5 3550H", physical_cores=4, logical_cores=8, max_clock_mhz=2100, socket="FP5"),
        ram=RAMInfo(total_gb=16.0, slots_used=2, speed_mhz=2667, ram_type="DDR4"),
        gpu=GPUInfo(name="NVIDIA GeForce GTX 1650", vram_gb=4.0, gpu_type="Dedicated"),
        motherboard=MotherboardInfo(
            manufacturer="ASUSTeK COMPUTER INC.",
            model="FX505DT",
            system_model="FX505DT-BI7N10",
        ),
        drives=[StorageInfo(name="Samsung SSD 970 EVO", size_gb=500.0, drive_type="NVMe SSD")],
        wifi=WiFiInfo(name="Intel(R) Wi-Fi 6 AX200 160MHz"),
        power=PowerInfo(
            battery_name="ASUS Battery",
            design_capacity_mwh=48000,
            full_charge_capacity_mwh=37440,
            health_pct=78,
            has_battery=True,
        ),
        system=SystemInfo(
            os_name="Windows 11 Home",
            os_version="10.0.26200",
            os_build="26200",
            os_install_date="2023-05-14",
            system_type="Laptop",
        ),
    )


@pytest.fixture
def unknown_specs() -> HardwareSpecs:
    """HardwareSpecs where every field is at its Unknown/fallback value."""
    return HardwareSpecs(
        cpu=CPUInfo(name="Unknown", physical_cores="Unknown", logical_cores="Unknown", max_clock_mhz="Unknown", socket="Unknown"),
        ram=RAMInfo(total_gb="Unknown", slots_used="Unknown", speed_mhz="Unknown", ram_type="Unknown"),
        gpu=GPUInfo(name="Unknown", vram_gb="Unknown", gpu_type="Unknown"),
        motherboard=MotherboardInfo(manufacturer="Unknown", model="Unknown", system_model="Unknown"),
        drives=[],
        wifi=WiFiInfo(name="Unknown"),
        power=PowerInfo(
            battery_name="Unknown",
            design_capacity_mwh="Unknown",
            full_charge_capacity_mwh="Unknown",
            health_pct="Unknown",
            has_battery=False,
        ),
        system=SystemInfo(
            os_name="Unknown",
            os_version="Unknown",
            os_build="Unknown",
            os_install_date="Unknown",
            system_type="Unknown",
        ),
    )


# ---- _fmt --------------------------------------------------------------------


def test_fmt_whole_float_drops_decimal() -> None:
    """Whole-number floats must drop the trailing '.0'."""
    assert _fmt(16.0) == "16"
    assert _fmt(4.0) == "4"


def test_fmt_fractional_float_preserved() -> None:
    """Fractional floats must keep their decimal part."""
    assert _fmt(13.9) == "13.9"


def test_fmt_none_and_unknown_render_as_unknown() -> None:
    """None and the string 'Unknown' must both render as 'Unknown'."""
    assert _fmt(None) == "Unknown"
    assert _fmt("Unknown") == "Unknown"


def test_fmt_integer_passthrough() -> None:
    """Plain integers pass through unchanged."""
    assert _fmt(2100) == "2100"
    assert _fmt(2) == "2"


def test_fmt_suffix_appended() -> None:
    """Suffix must concatenate cleanly onto any formatted value."""
    assert _fmt(2667, " MHz") == "2667 MHz"
    assert _fmt(16.0, " GB") == "16 GB"
    assert _fmt(None, " MHz") == "Unknown"


# ---- _parse_args -------------------------------------------------------------


def test_parse_args_defaults() -> None:
    """No flags: specs_only is False and model is the package default."""
    args = _parse_args([])
    assert args.specs_only is False
    assert args.model == DEFAULT_MODEL


def test_parse_args_specs_only_flag() -> None:
    """--specs-only must set specs_only to True."""
    args = _parse_args(["--specs-only"])
    assert args.specs_only is True


def test_parse_args_model_override() -> None:
    """--model must override the default model string."""
    args = _parse_args(["--model", "gemini-2.0-flash"])
    assert args.model == "gemini-2.0-flash"


def test_parse_args_explain_defaults_false() -> None:
    """explain must default to False when --explain is not supplied."""
    assert _parse_args([]).explain is False


def test_parse_args_explain_flag() -> None:
    """--explain must set explain to True."""
    assert _parse_args(["--explain"]).explain is True


def test_parse_args_version_exits_zero() -> None:
    """--version must exit with code 0."""
    with pytest.raises(SystemExit) as exc_info:
        _parse_args(["--version"])
    assert exc_info.value.code == 0


def test_parse_args_unknown_flag_exits_nonzero() -> None:
    """An unrecognised flag must exit with a non-zero code."""
    with pytest.raises(SystemExit) as exc_info:
        _parse_args(["--not-a-flag"])
    assert exc_info.value.code != 0


# ---- _print_specs ------------------------------------------------------------


def test_print_specs_cpu_name(capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs) -> None:
    """Output must contain the CPU name."""
    _print_specs(sample_specs)
    assert "AMD Ryzen 5 3550H" in capsys.readouterr().out


def test_print_specs_cpu_cores_and_clock(capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs) -> None:
    """Output must contain core count and clock speed without trailing .0."""
    _print_specs(sample_specs)
    out = capsys.readouterr().out
    assert "4c / 8t" in out
    assert "2100 MHz" in out
    assert "2100.0" not in out


def test_print_specs_ram(capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs) -> None:
    """Output must contain RAM capacity, type, speed, and slot count."""
    _print_specs(sample_specs)
    out = capsys.readouterr().out
    assert "16 GB" in out
    assert "DDR4" in out
    assert "2667 MHz" in out
    assert "2 slot(s)" in out


def test_print_specs_gpu(capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs) -> None:
    """Output must contain GPU name and VRAM without trailing .0."""
    _print_specs(sample_specs)
    out = capsys.readouterr().out
    assert "GTX 1650" in out
    assert "4 GB VRAM" in out
    assert "4.0 GB" not in out


def test_print_specs_shows_gpu_type(capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs) -> None:
    """Output must show the GPU type in brackets."""
    _print_specs(sample_specs)
    assert "[Dedicated]" in capsys.readouterr().out


def test_print_specs_omits_unknown_gpu_type(capsys: pytest.CaptureFixture, unknown_specs: HardwareSpecs) -> None:
    """'Unknown' GPU type must not appear bracketed in the output."""
    _print_specs(unknown_specs)
    assert "[Unknown]" not in capsys.readouterr().out


def test_print_specs_shows_cpu_socket(capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs) -> None:
    """Output must include the CPU socket designation."""
    _print_specs(sample_specs)
    assert "socket: FP5" in capsys.readouterr().out


def test_print_specs_motherboard(capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs) -> None:
    """Output must contain motherboard manufacturer and model."""
    _print_specs(sample_specs)
    out = capsys.readouterr().out
    assert "ASUSTeK" in out
    assert "FX505DT" in out


def test_print_specs_shows_system_model(capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs) -> None:
    """Output must include the bracketed full system model when available."""
    _print_specs(sample_specs)
    assert "[FX505DT-BI7N10]" in capsys.readouterr().out


def test_print_specs_omits_unknown_system_model(
    capsys: pytest.CaptureFixture, unknown_specs: HardwareSpecs
) -> None:
    """'Unknown' system_model must not appear bracketed in the output."""
    _print_specs(unknown_specs)
    assert "[Unknown]" not in capsys.readouterr().out


def test_print_specs_single_drive(capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs) -> None:
    """Output must show drive name, size, and type for a single drive."""
    _print_specs(sample_specs)
    out = capsys.readouterr().out
    assert "Samsung SSD 970 EVO" in out
    assert "500 GB" in out
    assert "NVMe SSD" in out


def test_print_specs_multiple_drives(capsys: pytest.CaptureFixture) -> None:
    """Output must list all drives when more than one is present."""
    specs = HardwareSpecs(
        cpu=CPUInfo(name="CPU", physical_cores=4, logical_cores=8, max_clock_mhz=3000, socket="LGA1200"),
        ram=RAMInfo(total_gb=16.0, slots_used=2, speed_mhz=3200, ram_type="DDR4"),
        gpu=GPUInfo(name="GPU", vram_gb=4.0, gpu_type="Dedicated"),
        motherboard=MotherboardInfo(manufacturer="Mfr", model="Mdl", system_model="Unknown"),
        drives=[
            StorageInfo(name="Samsung SSD 970 EVO", size_gb=500.0, drive_type="NVMe SSD"),
            StorageInfo(name="WDC WD10EZEX", size_gb=1000.0, drive_type="SATA HDD"),
        ],
        wifi=WiFiInfo(name="Unknown"),
        power=PowerInfo(battery_name="Unknown", design_capacity_mwh="Unknown",
                        full_charge_capacity_mwh="Unknown", health_pct="Unknown", has_battery=False),
        system=SystemInfo(os_name="Windows 11 Home", os_version="10.0.26200", os_build="26200",
                          os_install_date="2023-01-01", system_type="Desktop"),
    )
    _print_specs(specs)
    out = capsys.readouterr().out
    assert "Storage (2):" in out
    assert "Samsung SSD 970 EVO" in out
    assert "WDC WD10EZEX" in out


def test_print_specs_no_drives_shows_unknown(
    capsys: pytest.CaptureFixture, unknown_specs: HardwareSpecs
) -> None:
    """Empty drives list must display 'Storage: Unknown'."""
    _print_specs(unknown_specs)
    assert "Storage:     Unknown" in capsys.readouterr().out


def test_print_specs_no_double_space_unknown_ram_type(capsys: pytest.CaptureFixture) -> None:
    """Unknown RAM type must not produce a double space before '@'."""
    specs = HardwareSpecs(
        cpu=CPUInfo(name="CPU", physical_cores=4, logical_cores=8, max_clock_mhz=3000, socket="Unknown"),
        ram=RAMInfo(total_gb=8.0, slots_used=1, speed_mhz=3200, ram_type="Unknown"),
        gpu=GPUInfo(name="GPU", vram_gb=2.0, gpu_type="Dedicated"),
        motherboard=MotherboardInfo(manufacturer="Mfr", model="Mdl", system_model="Unknown"),
        drives=[],
        wifi=WiFiInfo(name="Unknown"),
        power=PowerInfo(battery_name="Unknown", design_capacity_mwh="Unknown",
                        full_charge_capacity_mwh="Unknown", health_pct="Unknown", has_battery=False),
        system=SystemInfo(os_name="Windows 11 Home", os_version="10.0.26200", os_build="26200",
                          os_install_date="2023-01-01", system_type="Desktop"),
    )
    _print_specs(specs)
    assert "  @" not in capsys.readouterr().out


# ---- main --------------------------------------------------------------------


def test_main_default_calls_collect_and_llm(sample_specs: HardwareSpecs) -> None:
    """Default run must call collect() and get_recommendations() exactly once."""
    with (
        patch("sys.argv", ["specs-ai"]),
        patch("specs_ai.cli.collect", return_value=sample_specs) as mock_collect,
        patch("specs_ai.cli.get_recommendations", return_value="Upgrade RAM.") as mock_recs,
    ):
        main()
    mock_collect.assert_called_once()
    mock_recs.assert_called_once()


def test_main_specs_only_skips_llm(sample_specs: HardwareSpecs) -> None:
    """--specs-only must call collect() but not get_recommendations()."""
    with (
        patch("sys.argv", ["specs-ai", "--specs-only"]),
        patch("specs_ai.cli.collect", return_value=sample_specs),
        patch("specs_ai.cli.get_recommendations") as mock_recs,
    ):
        main()
    mock_recs.assert_not_called()


def test_main_model_flag_forwarded(sample_specs: HardwareSpecs) -> None:
    """--model value must be passed through to get_recommendations."""
    with (
        patch("sys.argv", ["specs-ai", "--model", "gemini-2.0-flash"]),
        patch("specs_ai.cli.collect", return_value=sample_specs),
        patch("specs_ai.cli.get_recommendations", return_value="ok") as mock_recs,
    ):
        main()
    _, kwargs = mock_recs.call_args
    assert kwargs.get("model") == "gemini-2.0-flash"


def test_main_default_passes_verbose_false(sample_specs: HardwareSpecs) -> None:
    """Default run must pass verbose=False to get_recommendations."""
    with (
        patch("sys.argv", ["specs-ai"]),
        patch("specs_ai.cli.collect", return_value=sample_specs),
        patch("specs_ai.cli.get_recommendations", return_value="ok") as mock_recs,
    ):
        main()
    _, kwargs = mock_recs.call_args
    assert kwargs.get("verbose") is False


def test_main_explain_flag_passes_verbose_true(sample_specs: HardwareSpecs) -> None:
    """--explain must pass verbose=True to get_recommendations."""
    with (
        patch("sys.argv", ["specs-ai", "--explain"]),
        patch("specs_ai.cli.collect", return_value=sample_specs),
        patch("specs_ai.cli.get_recommendations", return_value="ok") as mock_recs,
    ):
        main()
    _, kwargs = mock_recs.call_args
    assert kwargs.get("verbose") is True


def test_main_environment_error_exits_1(
    capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs
) -> None:
    """EnvironmentError from get_recommendations must exit with code 1."""
    with (
        patch("sys.argv", ["specs-ai"]),
        patch("specs_ai.cli.collect", return_value=sample_specs),
        patch("specs_ai.cli.get_recommendations", side_effect=EnvironmentError("no key")),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()
    assert exc_info.value.code == 1
    assert "no key" in capsys.readouterr().err


def test_main_runtime_error_exits_1(
    capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs
) -> None:
    """RuntimeError from get_recommendations must exit with code 1."""
    with (
        patch("sys.argv", ["specs-ai"]),
        patch("specs_ai.cli.collect", return_value=sample_specs),
        patch("specs_ai.cli.get_recommendations", side_effect=RuntimeError("network down")),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()
    assert exc_info.value.code == 1
    assert "network down" in capsys.readouterr().err


def test_main_prints_recommendations(
    capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs
) -> None:
    """Recommendation text from get_recommendations must appear in stdout."""
    with (
        patch("sys.argv", ["specs-ai"]),
        patch("specs_ai.cli.collect", return_value=sample_specs),
        patch("specs_ai.cli.get_recommendations", return_value="Add more RAM."),
    ):
        main()
    assert "Add more RAM." in capsys.readouterr().out


def test_print_specs_shows_wifi_name(capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs) -> None:
    """Output must contain the WiFi adapter name."""
    _print_specs(sample_specs)
    assert "Intel(R) Wi-Fi 6 AX200 160MHz" in capsys.readouterr().out


def test_print_specs_shows_unknown_wifi(capsys: pytest.CaptureFixture, unknown_specs: HardwareSpecs) -> None:
    """'Unknown' WiFi must still appear in output (not silently omitted)."""
    _print_specs(unknown_specs)
    assert "WiFi:" in capsys.readouterr().out


def test_print_specs_shows_battery_health(capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs) -> None:
    """Laptop battery name and health percentage must appear in output."""
    _print_specs(sample_specs)
    out = capsys.readouterr().out
    assert "ASUS Battery" in out
    assert "78%" in out
    assert "48000 mWh" in out


def test_print_specs_laptop_partial_battery_data(capsys: pytest.CaptureFixture) -> None:
    """Laptop with battery present but capacity readings missing must show only Health."""
    specs = HardwareSpecs(
        cpu=CPUInfo(name="CPU", physical_cores=4, logical_cores=8, max_clock_mhz=3000, socket="BGA1440"),
        ram=RAMInfo(total_gb=16.0, slots_used=2, speed_mhz=3200, ram_type="DDR4"),
        gpu=GPUInfo(name="GPU", vram_gb=4.0, gpu_type="Dedicated"),
        motherboard=MotherboardInfo(manufacturer="Mfr", model="Mdl", system_model="Unknown"),
        drives=[],
        wifi=WiFiInfo(name="Unknown"),
        power=PowerInfo(
            battery_name="ASUS Battery",
            design_capacity_mwh="Unknown",
            full_charge_capacity_mwh="Unknown",
            health_pct="Unknown",
            has_battery=True,
        ),
        system=SystemInfo(os_name="Windows 11 Home", os_version="10.0.26200", os_build="26200",
                          os_install_date="2023-01-01", system_type="Laptop"),
    )
    _print_specs(specs)
    out = capsys.readouterr().out
    assert "ASUS Battery" in out
    assert "Health: Unknown" in out
    assert "mWh" not in out  # capacity tail must be absent


def test_print_specs_desktop_shows_psu_callout(capsys: pytest.CaptureFixture, unknown_specs: HardwareSpecs) -> None:
    """Desktop (has_battery=False) must show a note that PSU and battery are not available."""
    _print_specs(unknown_specs)
    out = capsys.readouterr().out
    assert "Desktop" in out
    assert "PSU" in out
    assert "Battery" not in out


def test_print_specs_shows_os_name(capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs) -> None:
    """Output must contain the OS name."""
    _print_specs(sample_specs)
    assert "Windows 11 Home" in capsys.readouterr().out


def test_print_specs_shows_os_build(capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs) -> None:
    """Output must contain the OS build number."""
    _print_specs(sample_specs)
    assert "26200" in capsys.readouterr().out


def test_print_specs_shows_os_install_date(capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs) -> None:
    """Output must contain the OS install date."""
    _print_specs(sample_specs)
    assert "2023-05-14" in capsys.readouterr().out


def test_print_specs_shows_system_type(capsys: pytest.CaptureFixture, sample_specs: HardwareSpecs) -> None:
    """Output must show the system type (Laptop / Desktop)."""
    _print_specs(sample_specs)
    assert "Laptop" in capsys.readouterr().out
