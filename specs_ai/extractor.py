"""Hardware spec extraction using WMI and psutil."""

import struct
import winreg
from dataclasses import dataclass

import psutil
import wmi


_MEMORY_TYPE_MAP: dict[int, str] = {
    20: "DDR",
    21: "DDR2",
    22: "DDR2 FB-DIMM",
    24: "DDR3",
    26: "DDR4",
    34: "DDR5",
}

_VIRTUAL_GPU_NAMES: tuple[str, ...] = (
    "microsoft basic display",
    "microsoft remote display",
    "citrix indirect display",
    "vmware",
    "virtualbox",
    "hyper-v",
    "parsec",
    "displaylink",
)

_GENERIC_BOARD_STRINGS: frozenset[str] = frozenset(
    {
        "to be filled by o.e.m.",
        "default string",
        "system manufacturer",
        "system product name",
        "not specified",
        "not available",
        "none",
        "n/a",
        "",
    }
)


@dataclass
class CPUInfo:
    """CPU identification and performance specs."""

    name: str
    physical_cores: int | str
    logical_cores: int | str
    max_clock_mhz: int | str


@dataclass
class RAMInfo:
    """Installed RAM capacity, slot usage, speed, and generation."""

    total_gb: float | str
    slots_used: int | str
    speed_mhz: int | str
    ram_type: str


@dataclass
class GPUInfo:
    """Primary GPU name and reported VRAM."""

    name: str
    vram_gb: float | str


@dataclass
class MotherboardInfo:
    """Motherboard manufacturer, product model, and full OEM system product name."""

    manufacturer: str
    model: str
    system_model: str  # Win32_ComputerSystemProduct.Name — may carry variant suffix


@dataclass
class HardwareSpecs:
    """Complete hardware snapshot of the local machine."""

    cpu: CPUInfo
    ram: RAMInfo
    gpu: GPUInfo
    motherboard: MotherboardInfo


def _clean_board_string(value: str | None) -> str:
    """Return a cleaned BIOS string, or 'Unknown' for known placeholder values."""
    if value is None:
        return "Unknown"
    cleaned = value.strip()
    if cleaned.lower() in _GENERIC_BOARD_STRINGS:
        return "Unknown"
    return cleaned


def _is_real_gpu(name: str | None) -> bool:
    """Return False for virtual or fallback display adapters."""
    if not name:
        return False
    lower = name.lower()
    return not any(virt in lower for virt in _VIRTUAL_GPU_NAMES)


def _adapter_ram_to_bytes(adapter_ram: object) -> int:
    """Coerce WMI Win32_VideoController.AdapterRAM to unsigned bytes.

    pywin32 surfaces the underlying uint32 as a signed Python int, so values
    >= 2 GB appear negative. Re-add 2**32 to recover the unsigned value.
    Note: actual VRAM >= 4 GB still cannot be represented (overflows to ~0);
    use _vram_from_registry for those cases.
    """
    if adapter_ram is None:
        return 0
    try:
        val = int(adapter_ram)
    except (TypeError, ValueError):
        return 0
    if val < 0:
        val += 2**32
    return max(val, 0)


def _get_cpu() -> CPUInfo:
    """Extract CPU name, core counts, and max clock speed via WMI and psutil."""
    name: str = "Unknown"
    max_clock: int | str = "Unknown"
    try:
        proc = wmi.WMI().Win32_Processor()[0]
        name = proc.Name.strip() if proc.Name else "Unknown"
        max_clock = int(proc.MaxClockSpeed) if proc.MaxClockSpeed else "Unknown"
    except Exception:
        pass

    physical: int | str = "Unknown"
    logical: int | str = "Unknown"
    try:
        physical = psutil.cpu_count(logical=False) or "Unknown"
        logical = psutil.cpu_count(logical=True) or "Unknown"
    except Exception:
        pass

    return CPUInfo(
        name=name,
        physical_cores=physical,
        logical_cores=logical,
        max_clock_mhz=max_clock,
    )


def _get_ram() -> RAMInfo:
    """Extract installed RAM, slot count, speed, and memory type via WMI.

    Total capacity is summed from Win32_PhysicalMemory (installed amount),
    not psutil.virtual_memory().total which reports only OS-usable memory
    after BIOS/iGPU reservations.
    """
    total_gb: float | str = "Unknown"
    slots_used: int | str = "Unknown"
    speed_mhz: int | str = "Unknown"
    ram_type: str = "Unknown"

    try:
        sticks = wmi.WMI().Win32_PhysicalMemory()
        slots_used = len(sticks)

        capacities = [int(s.Capacity) for s in sticks if s.Capacity]
        if capacities:
            total_gb = round(sum(capacities) / (1024**3), 1)

        # System runs at the speed of the slowest installed stick.
        speeds = [int(s.Speed) for s in sticks if s.Speed]
        if speeds:
            speed_mhz = min(speeds)

        types = [int(s.SMBIOSMemoryType) for s in sticks if s.SMBIOSMemoryType]
        if types:
            ram_type = _MEMORY_TYPE_MAP.get(types[0], "Unknown")
    except Exception:
        pass

    if total_gb == "Unknown":
        try:
            total_gb = round(psutil.virtual_memory().total / (1024**3), 1)
        except Exception:
            pass

    return RAMInfo(
        total_gb=total_gb,
        slots_used=slots_used,
        speed_mhz=speed_mhz,
        ram_type=ram_type,
    )


_GPU_REG_KEY = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"


def _vram_from_registry(gpu_name: str) -> float | str:
    """Read VRAM from the Windows registry as a fallback for WMI AdapterRAM overflow.

    WMI reports AdapterRAM as a 32-bit DWORD, so values >= 4 GB overflow.
    The registry stores the same value as a 64-bit QWORD under the GPU driver
    subkey, avoiding the overflow entirely.
    """
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _GPU_REG_KEY) as base:
            idx = 0
            while True:
                try:
                    sub_name = winreg.EnumKey(base, idx)
                    idx += 1
                    with winreg.OpenKey(base, sub_name) as sub:
                        try:
                            desc, _ = winreg.QueryValueEx(sub, "DriverDesc")
                        except OSError:
                            continue
                        name_match = (
                            gpu_name.lower() in desc.lower()
                            or desc.lower() in gpu_name.lower()
                        )
                        if not name_match:
                            continue
                        try:
                            raw, reg_type = winreg.QueryValueEx(
                                sub, "HardwareInformation.MemorySize"
                            )
                            if reg_type == winreg.REG_DWORD:
                                mem_bytes: int = raw
                            elif reg_type == winreg.REG_QWORD:
                                # winreg returns REG_QWORD as a plain Python int
                                mem_bytes = raw
                            elif reg_type == winreg.REG_BINARY and len(raw) == 4:
                                mem_bytes = struct.unpack("<I", raw)[0]
                            elif reg_type == winreg.REG_BINARY and len(raw) == 8:
                                mem_bytes = struct.unpack("<Q", raw)[0]
                            else:
                                continue
                            if mem_bytes > 0:
                                return round(mem_bytes / (1024**3), 1)
                        except OSError:
                            pass
                except OSError:
                    break
    except Exception:
        pass
    return "Unknown"


def _get_gpu() -> GPUInfo:
    """Extract GPU name and VRAM via WMI, preferring registry for accurate VRAM.

    Filters out virtual display adapters (Microsoft Basic, RDP, Citrix, VM
    adapters). Among real GPUs, picks the one with the highest VRAM — which
    is reliably the discrete GPU on hybrid laptops. WMI AdapterRAM is unreliable
    (32-bit DWORD overflow), so registry is the primary source; AdapterRAM is
    only a last-resort fallback.
    """
    name: str = "Unknown"
    vram_gb: float | str = "Unknown"
    try:
        all_controllers = wmi.WMI().Win32_VideoController()
        controllers = [g for g in all_controllers if _is_real_gpu(g.Name)]
        if not controllers:
            return GPUInfo(name=name, vram_gb=vram_gb)

        scored: list[tuple[float, str]] = []
        for g in controllers:
            g_name = g.Name.strip() if g.Name else "Unknown"
            reg_vram = _vram_from_registry(g_name)
            if isinstance(reg_vram, float):
                vram = reg_vram
            else:
                raw_bytes = _adapter_ram_to_bytes(g.AdapterRAM)
                vram = round(raw_bytes / (1024**3), 1) if raw_bytes > 0 else 0.0
            scored.append((vram, g_name))

        scored.sort(key=lambda x: x[0], reverse=True)
        best_vram, best_name = scored[0]
        name = best_name
        vram_gb = best_vram if best_vram > 0 else "Unknown"
    except Exception:
        pass

    return GPUInfo(name=name, vram_gb=vram_gb)


def _get_motherboard() -> MotherboardInfo:
    """Extract motherboard and full system product name via WMI.

    Win32_BaseBoard gives board-level manufacturer/model (e.g. "FX505DT").
    Win32_ComputerSystemProduct.Name often carries the full OEM variant string
    (e.g. "FX505DT-BI7N10") that BaseBoard.Product truncates. Falls back to
    Win32_ComputerSystem.Model if ComputerSystemProduct returns nothing useful.
    All strings are filtered through _clean_board_string to discard placeholders.
    """
    manufacturer: str = "Unknown"
    model: str = "Unknown"
    system_model: str = "Unknown"

    try:
        board = wmi.WMI().Win32_BaseBoard()[0]
        manufacturer = _clean_board_string(board.Manufacturer)
        model = _clean_board_string(board.Product)
    except Exception:
        pass

    try:
        csp = wmi.WMI().Win32_ComputerSystemProduct()[0]
        system_model = _clean_board_string(csp.Name)
    except Exception:
        pass

    if system_model == "Unknown":
        try:
            cs = wmi.WMI().Win32_ComputerSystem()[0]
            system_model = _clean_board_string(cs.Model)
        except Exception:
            pass

    return MotherboardInfo(manufacturer=manufacturer, model=model, system_model=system_model)


def collect() -> HardwareSpecs:
    """Collect all hardware specs from this machine and return a HardwareSpecs instance."""
    return HardwareSpecs(
        cpu=_get_cpu(),
        ram=_get_ram(),
        gpu=_get_gpu(),
        motherboard=_get_motherboard(),
    )
