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


@dataclass
class CPUInfo:
    """CPU identification and performance specs."""

    name: str
    physical_cores: int | str
    logical_cores: int | str
    max_clock_mhz: float | str


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
    """Motherboard manufacturer and product model."""

    manufacturer: str
    model: str


@dataclass
class HardwareSpecs:
    """Complete hardware snapshot of the local machine."""

    cpu: CPUInfo
    ram: RAMInfo
    gpu: GPUInfo
    motherboard: MotherboardInfo


def _get_cpu() -> CPUInfo:
    """Extract CPU name, core counts, and max clock speed via WMI and psutil."""
    name: str = "Unknown"
    max_clock: float | str = "Unknown"
    try:
        proc = wmi.WMI().Win32_Processor()[0]
        name = proc.Name.strip() if proc.Name else "Unknown"
        max_clock = float(proc.MaxClockSpeed) if proc.MaxClockSpeed else "Unknown"
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
    """Extract total RAM, slot count, speed, and memory type via WMI and psutil."""
    total_gb: float | str = "Unknown"
    try:
        total_gb = round(psutil.virtual_memory().total / (1024**3), 1)
    except Exception:
        pass

    slots_used: int | str = "Unknown"
    speed_mhz: int | str = "Unknown"
    ram_type: str = "Unknown"
    try:
        sticks = wmi.WMI().Win32_PhysicalMemory()
        slots_used = len(sticks)
        speeds = [int(s.Speed) for s in sticks if s.Speed]
        speed_mhz = speeds[0] if speeds else "Unknown"
        types = [int(s.SMBIOSMemoryType) for s in sticks if s.SMBIOSMemoryType]
        ram_type = _MEMORY_TYPE_MAP.get(types[0], "Unknown") if types else "Unknown"
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

    WMI reports AdapterRAM as a 32-bit DWORD, so values >= 4 GB overflow to 0.
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
    """Extract GPU name and VRAM via WMI, with registry fallback for VRAM overflow."""
    name: str = "Unknown"
    vram_gb: float | str = "Unknown"
    try:
        controllers = wmi.WMI().Win32_VideoController()
        # Prefer discrete GPU: pick controller with most reported VRAM first,
        # then fall back to first entry if all report 0 (overflow case).
        controllers.sort(key=lambda g: int(g.AdapterRAM or 0), reverse=True)
        gpu = controllers[0]
        name = gpu.Name.strip() if gpu.Name else "Unknown"
        ram_bytes = int(gpu.AdapterRAM or 0)
        if ram_bytes > 0:
            vram_gb = round(ram_bytes / (1024**3), 1)
        else:
            vram_gb = _vram_from_registry(name)
    except Exception:
        pass

    return GPUInfo(name=name, vram_gb=vram_gb)


def _get_motherboard() -> MotherboardInfo:
    """Extract motherboard manufacturer and product name via WMI Win32_BaseBoard."""
    manufacturer: str = "Unknown"
    model: str = "Unknown"
    try:
        board = wmi.WMI().Win32_BaseBoard()[0]
        manufacturer = board.Manufacturer.strip() if board.Manufacturer else "Unknown"
        model = board.Product.strip() if board.Product else "Unknown"
    except Exception:
        pass

    return MotherboardInfo(manufacturer=manufacturer, model=model)


def collect() -> HardwareSpecs:
    """Collect all hardware specs from this machine and return a HardwareSpecs instance."""
    return HardwareSpecs(
        cpu=_get_cpu(),
        ram=_get_ram(),
        gpu=_get_gpu(),
        motherboard=_get_motherboard(),
    )
