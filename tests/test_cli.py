"""Tests for cli.py."""

from unittest.mock import patch

import pytest

from specs_ai.cli import _DEFAULT_MODEL, _fmt, _parse_args, _print_specs, main
from specs_ai.extractor import CPUInfo, GPUInfo, HardwareSpecs, MotherboardInfo, RAMInfo


# ---- fixtures ----------------------------------------------------------------


@pytest.fixture
def sample_specs() -> HardwareSpecs:
    """Realistic HardwareSpecs snapshot used across multiple tests."""
    return HardwareSpecs(
        cpu=CPUInfo(name="AMD Ryzen 5 3550H", physical_cores=4, logical_cores=8, max_clock_mhz=2100),
        ram=RAMInfo(total_gb=16.0, slots_used=2, speed_mhz=2667, ram_type="DDR4"),
        gpu=GPUInfo(name="NVIDIA GeForce GTX 1650", vram_gb=4.0),
        motherboard=MotherboardInfo(
            manufacturer="ASUSTeK COMPUTER INC.",
            model="FX505DT",
            system_model="FX505DT-BI7N10",
        ),
    )


@pytest.fixture
def unknown_specs() -> HardwareSpecs:
    """HardwareSpecs where every field is at its Unknown/fallback value."""
    return HardwareSpecs(
        cpu=CPUInfo(name="Unknown", physical_cores="Unknown", logical_cores="Unknown", max_clock_mhz="Unknown"),
        ram=RAMInfo(total_gb="Unknown", slots_used="Unknown", speed_mhz="Unknown", ram_type="Unknown"),
        gpu=GPUInfo(name="Unknown", vram_gb="Unknown"),
        motherboard=MotherboardInfo(manufacturer="Unknown", model="Unknown", system_model="Unknown"),
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
    assert args.model == _DEFAULT_MODEL


def test_parse_args_specs_only_flag() -> None:
    """--specs-only must set specs_only to True."""
    args = _parse_args(["--specs-only"])
    assert args.specs_only is True


def test_parse_args_model_override() -> None:
    """--model must override the default model string."""
    args = _parse_args(["--model", "gemini-2.0-flash"])
    assert args.model == "gemini-2.0-flash"


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


def test_print_specs_no_double_space_unknown_ram_type(capsys: pytest.CaptureFixture) -> None:
    """Unknown RAM type must not produce a double space before '@'."""
    specs = HardwareSpecs(
        cpu=CPUInfo(name="CPU", physical_cores=4, logical_cores=8, max_clock_mhz=3000),
        ram=RAMInfo(total_gb=8.0, slots_used=1, speed_mhz=3200, ram_type="Unknown"),
        gpu=GPUInfo(name="GPU", vram_gb=2.0),
        motherboard=MotherboardInfo(manufacturer="Mfr", model="Mdl", system_model="Unknown"),
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
