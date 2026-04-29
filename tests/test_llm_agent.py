"""Tests for llm_agent.py."""

from unittest.mock import MagicMock, patch

import pytest

from specs_ai.llm_agent import (
    _build_prompt,
    _format_value,
    _load_api_key,
    get_recommendations,
)

_SAMPLE_SPECS: dict = {
    "cpu": {
        "name": "AMD Ryzen 5 3550H",
        "physical_cores": 4,
        "logical_cores": 8,
        "max_clock_mhz": 2100,
    },
    "ram": {
        "total_gb": 16.0,
        "slots_used": 2,
        "speed_mhz": 2667,
        "ram_type": "DDR4",
    },
    "gpu": {"name": "NVIDIA GeForce GTX 1650", "vram_gb": 4.0},
    "motherboard": {"manufacturer": "ASUSTeK COMPUTER INC.", "model": "FX505DT", "system_model": "FX505DT-BI7N10"},
    "drives": [
        {"name": "Samsung SSD 970 EVO", "size_gb": 500.0, "drive_type": "NVMe SSD"},
    ],
    "wifi": {"name": "Intel(R) Wi-Fi 6 AX200 160MHz"},
    "power": {
        "battery_name": "ASUS Battery",
        "design_capacity_mwh": 48000,
        "full_charge_capacity_mwh": 37440,
        "health_pct": 78,
        "has_battery": True,
    },
}


# ---- _build_prompt ----------------------------------------------------------


def test_build_prompt_contains_cpu_name() -> None:
    """Prompt must include the CPU name."""
    assert "AMD Ryzen 5 3550H" in _build_prompt(_SAMPLE_SPECS)


def test_build_prompt_contains_gpu_name() -> None:
    """Prompt must include the GPU name."""
    assert "GTX 1650" in _build_prompt(_SAMPLE_SPECS)


def test_build_prompt_contains_ram_type() -> None:
    """Prompt must include the RAM type."""
    assert "DDR4" in _build_prompt(_SAMPLE_SPECS)


def test_build_prompt_contains_motherboard() -> None:
    """Prompt must include the motherboard model."""
    assert "FX505DT" in _build_prompt(_SAMPLE_SPECS)


def test_build_prompt_contains_system_model() -> None:
    """Prompt must include the full OEM system model when provided."""
    assert "FX505DT-BI7N10" in _build_prompt(_SAMPLE_SPECS)


def test_build_prompt_omits_system_model_bracket_when_unknown() -> None:
    """No bracketed system_model must appear when the value is 'Unknown'."""
    specs = dict(_SAMPLE_SPECS)
    specs["motherboard"] = {"manufacturer": "ASUSTeK COMPUTER INC.", "model": "FX505DT", "system_model": "Unknown"}
    prompt = _build_prompt(specs)
    assert "[Unknown]" not in prompt


def test_build_prompt_handles_unknown_fields() -> None:
    """Prompt must not raise when fields are missing or 'Unknown'."""
    sparse = {"cpu": {"name": "Unknown"}, "ram": {}, "gpu": {}, "motherboard": {}}
    prompt = _build_prompt(sparse)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_build_prompt_handles_none_sub_dicts() -> None:
    """Prompt must tolerate None values in place of nested dicts."""
    weird = {"cpu": None, "ram": None, "gpu": None, "motherboard": None}
    prompt = _build_prompt(weird)
    assert isinstance(prompt, str)
    assert "Unknown" in prompt


def test_build_prompt_strips_trailing_float_zero() -> None:
    """Whole-number floats must render without the trailing '.0'."""
    prompt = _build_prompt(_SAMPLE_SPECS)
    assert "2100.0 MHz" not in prompt
    assert "2100 MHz" in prompt
    assert "16.0 GB" not in prompt
    assert "16 GB" in prompt


def test_build_prompt_collapses_unknown_ram_type() -> None:
    """An 'Unknown' or empty RAM type must not produce a stray double space."""
    specs = {
        "cpu": {},
        "ram": {"total_gb": 16.0, "ram_type": "Unknown", "speed_mhz": 2667},
        "gpu": {},
        "motherboard": {},
    }
    prompt = _build_prompt(specs)
    assert "Unknown @" not in prompt
    assert "GB  @" not in prompt


def test_build_prompt_is_ascii_safe() -> None:
    """Prompt should use only ASCII to avoid Windows console encoding issues."""
    prompt = _build_prompt(_SAMPLE_SPECS)
    prompt.encode("ascii")  # raises UnicodeEncodeError if any non-ASCII present


def test_build_prompt_restricts_to_listed_components() -> None:
    """Prompt must instruct the LLM not to recommend unlisted components."""
    prompt = _build_prompt(_SAMPLE_SPECS)
    assert "Do NOT mention, assume, or speculate about components that are not listed" in prompt
    assert "PSU" in prompt  # PSU remains excluded — we cannot detect it


def test_build_prompt_storage_now_listed_not_excluded() -> None:
    """Storage must appear in the listed-components clause, not the exclusion clause."""
    prompt = _build_prompt(_SAMPLE_SPECS)
    assert "Storage" in prompt  # listed as a known component
    assert "storage, PSU" not in prompt  # no longer in the exclusion list


def test_build_prompt_contains_drive_name() -> None:
    """Prompt must include the drive model name."""
    assert "Samsung SSD 970 EVO" in _build_prompt(_SAMPLE_SPECS)


def test_build_prompt_contains_drive_type() -> None:
    """Prompt must include the drive type (e.g. NVMe SSD)."""
    assert "NVMe SSD" in _build_prompt(_SAMPLE_SPECS)


def test_build_prompt_storage_unknown_when_no_drives() -> None:
    """Prompt must show 'Storage: Unknown' when drives list is empty."""
    specs = dict(_SAMPLE_SPECS)
    specs["drives"] = []
    assert "Storage:     Unknown" in _build_prompt(specs)


def test_build_prompt_handles_multiple_drives() -> None:
    """Prompt must list all drives when there are more than one."""
    specs = dict(_SAMPLE_SPECS)
    specs["drives"] = [
        {"name": "Samsung SSD 970 EVO", "size_gb": 500.0, "drive_type": "NVMe SSD"},
        {"name": "WDC WD10EZEX", "size_gb": 1000.0, "drive_type": "SATA HDD"},
    ]
    prompt = _build_prompt(specs)
    assert "Samsung SSD 970 EVO" in prompt
    assert "WDC WD10EZEX" in prompt


def test_build_prompt_scopes_closing_question() -> None:
    """Closing question must be scoped to listed components, not open-ended."""
    prompt = _build_prompt(_SAMPLE_SPECS)
    assert "components listed above" in prompt
    assert "What are the best upgrade paths for this machine?" not in prompt


def test_build_prompt_contains_wifi_name() -> None:
    """Prompt must include the WiFi adapter name."""
    assert "Intel(R) Wi-Fi 6 AX200 160MHz" in _build_prompt(_SAMPLE_SPECS)


def test_build_prompt_wifi_in_listed_components() -> None:
    """WiFi must appear in the listed-components IMPORTANT clause."""
    prompt = _build_prompt(_SAMPLE_SPECS)
    assert "WiFi" in prompt
    # The IMPORTANT clause must name WiFi alongside the other tracked components.
    assert "CPU, RAM, GPU, Motherboard, Storage, WiFi, Battery" in prompt


def test_build_prompt_contains_battery_name() -> None:
    """Prompt must include the battery name for laptops."""
    assert "ASUS Battery" in _build_prompt(_SAMPLE_SPECS)


def test_build_prompt_contains_battery_health() -> None:
    """Prompt must include the battery health percentage for laptops."""
    assert "78%" in _build_prompt(_SAMPLE_SPECS)


def test_build_prompt_battery_in_listed_components() -> None:
    """Battery must appear in the listed-components IMPORTANT clause."""
    prompt = _build_prompt(_SAMPLE_SPECS)
    assert "CPU, RAM, GPU, Motherboard, Storage, WiFi, Battery" in prompt


def test_build_prompt_battery_replacement_callout() -> None:
    """Prompt must warn about difficulty sourcing genuine OEM battery replacements."""
    prompt = _build_prompt(_SAMPLE_SPECS)
    assert "original parts" in prompt


def test_build_prompt_laptop_partial_battery_data() -> None:
    """Laptop with battery present but capacity readings missing must omit the capacity tail."""
    specs = dict(_SAMPLE_SPECS)
    specs["power"] = {
        "battery_name": "ASUS Battery",
        "design_capacity_mwh": "Unknown",
        "full_charge_capacity_mwh": "Unknown",
        "health_pct": "Unknown",
        "has_battery": True,
    }
    prompt = _build_prompt(specs)
    assert "ASUS Battery" in prompt
    assert "Health: Unknown" in prompt
    assert "mWh" not in prompt  # capacity tail must be absent
    assert "original parts" in prompt  # OEM callout still applies on laptops


def test_build_prompt_desktop_shows_psu_callout() -> None:
    """Desktop prompt must note that PSU/battery are unavailable, with no Battery section."""
    specs = dict(_SAMPLE_SPECS)
    specs["power"] = {
        "battery_name": "Unknown",
        "design_capacity_mwh": "Unknown",
        "full_charge_capacity_mwh": "Unknown",
        "health_pct": "Unknown",
        "has_battery": False,
    }
    prompt = _build_prompt(specs)
    assert "Desktop" in prompt
    assert "PSU" in prompt
    assert "Battery" not in prompt
    assert "original parts" not in prompt  # OEM callout must also be absent


# ---- _format_value ----------------------------------------------------------


def test_format_value_integer_float() -> None:
    """Whole-number floats must drop the '.0'."""
    assert _format_value(2100.0) == "2100"
    assert _format_value(16.0) == "16"


def test_format_value_fractional_float() -> None:
    """Fractional floats must keep their decimal."""
    assert _format_value(13.9) == "13.9"


def test_format_value_unknown_passthrough() -> None:
    """'Unknown' and None must render as 'Unknown'."""
    assert _format_value("Unknown") == "Unknown"
    assert _format_value(None) == "Unknown"


def test_format_value_with_suffix() -> None:
    """Suffix (e.g. ' MHz') must concatenate cleanly."""
    assert _format_value(2667, " MHz") == "2667 MHz"


# ---- _load_api_key ----------------------------------------------------------


def test_load_api_key_returns_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should return the key when the env var is set."""
    monkeypatch.setenv("SPECS_AI_API_KEY", "test-key-abc")
    assert _load_api_key() == "test-key-abc"


def test_load_api_key_strips_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Leading/trailing whitespace must be stripped from the key."""
    monkeypatch.setenv("SPECS_AI_API_KEY", "  real-key  ")
    assert _load_api_key() == "real-key"


def test_load_api_key_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should raise EnvironmentError with setup instructions when key is absent."""
    monkeypatch.delenv("SPECS_AI_API_KEY", raising=False)
    with patch("specs_ai.llm_agent.load_dotenv"):  # prevent real .env from loading
        with pytest.raises(EnvironmentError, match="SPECS_AI_API_KEY"):
            _load_api_key()


def test_load_api_key_error_includes_instructions(monkeypatch: pytest.MonkeyPatch) -> None:
    """EnvironmentError message must include setup instructions."""
    monkeypatch.delenv("SPECS_AI_API_KEY", raising=False)
    with patch("specs_ai.llm_agent.load_dotenv"):
        with pytest.raises(EnvironmentError, match=r"\.env"):
            _load_api_key()


def test_load_api_key_rejects_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    """The .env.example placeholder must be detected and rejected."""
    monkeypatch.setenv("SPECS_AI_API_KEY", "your-gemini-api-key-here")
    with patch("specs_ai.llm_agent.load_dotenv"):
        with pytest.raises(EnvironmentError, match="placeholder"):
            _load_api_key()


def test_load_api_key_rejects_other_placeholders(monkeypatch: pytest.MonkeyPatch) -> None:
    """Common stand-in values must also be rejected, case-insensitively."""
    for placeholder in ("YOUR-KEY", "ChangeMe", "your-api-key"):
        monkeypatch.setenv("SPECS_AI_API_KEY", placeholder)
        with patch("specs_ai.llm_agent.load_dotenv"):
            with pytest.raises(EnvironmentError):
                _load_api_key()


# ---- get_recommendations ----------------------------------------------------


def test_get_recommendations_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Happy path: real-looking text from the model is returned verbatim."""
    monkeypatch.setenv("SPECS_AI_API_KEY", "real-test-key")
    fake_response = MagicMock(text="Add more RAM, upgrade GPU.")
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response
    with patch("specs_ai.llm_agent.genai.Client", return_value=fake_client):
        result = get_recommendations(_SAMPLE_SPECS)
    assert result == "Add more RAM, upgrade GPU."


def test_get_recommendations_handles_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty / falsy response.text must yield a clear placeholder string."""
    monkeypatch.setenv("SPECS_AI_API_KEY", "real-test-key")
    fake_response = MagicMock(text=None)
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response
    with patch("specs_ai.llm_agent.genai.Client", return_value=fake_client):
        result = get_recommendations(_SAMPLE_SPECS)
    assert "No recommendations" in result


def test_get_recommendations_wraps_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Underlying API exceptions must be wrapped as RuntimeError."""
    monkeypatch.setenv("SPECS_AI_API_KEY", "real-test-key")
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = ConnectionError("network down")
    with patch("specs_ai.llm_agent.genai.Client", return_value=fake_client):
        with pytest.raises(RuntimeError, match="Gemini API call failed"):
            get_recommendations(_SAMPLE_SPECS)


def test_get_recommendations_propagates_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the key is missing, the EnvironmentError surfaces before any API call."""
    monkeypatch.delenv("SPECS_AI_API_KEY", raising=False)
    with patch("specs_ai.llm_agent.load_dotenv"), patch(
        "specs_ai.llm_agent.genai.Client"
    ) as fake_client:
        with pytest.raises(EnvironmentError):
            get_recommendations(_SAMPLE_SPECS)
        fake_client.assert_not_called()
