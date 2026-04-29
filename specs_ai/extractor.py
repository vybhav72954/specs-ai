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

_BUS_TYPE_NAMES: dict[int, str] = {
    3: "ATA",
    11: "SATA",
    17: "NVMe",
}

_MEDIA_TYPE_NAMES: dict[int, str] = {
    3: "HDD",
    4: "SSD",
}

# Bus types that indicate removable media — excluded from storage reporting.
_REMOVABLE_BUS_TYPES: frozenset[int] = frozenset({7, 12, 13})  # USB, SD, MMC

# Substrings that identify an adapter as WiFi (checked against lowercased name/type).
_WIFI_KEYWORDS: tuple[str, ...] = ("wi-fi", "wifi", "wireless", "wlan", "802.11")

# Win32_ComputerSystem.PCSystemType → human-readable form factor.
_PC_SYSTEM_TYPES: dict[int, str] = {
    1: "Desktop",
    2: "Laptop",
    3: "Workstation",
    8: "Laptop",  # Slate / tablet
}

# Virtual/software WiFi adapters to exclude (checked against lowercased name).
_VIRTUAL_WIFI_KEYWORDS: tuple[str, ...] = (
    "microsoft wi-fi direct",
    "microsoft hosted network",
    "virtual",
    "bluetooth",  # BT adapters sometimes surface alongside the combo card
)

# Substrings that identify a GPU as integrated (checked against lowercased name).
# Avoid vendor-prefixed terms like "intel uhd" — the "(R)" trademark symbol in
# WMI names ("Intel(R) UHD Graphics 630") breaks that match.
_INTEGRATED_GPU_KEYWORDS: tuple[str, ...] = (
    "uhd graphics",     # Intel UHD — appears after the (R) marker
    "hd graphics",      # Intel HD — same; also covers "Intel HD Graphics NNN"
    "iris",             # Intel Iris / Iris Xe / Iris Plus
    "radeon graphics",  # "AMD Radeon Graphics" — generic Ryzen/APU iGPU label
    "adreno",           # Qualcomm Snapdragon iGPU
)


@dataclass
class CPUInfo:
    """CPU identification and performance specs."""

    name: str
    physical_cores: int | str
    logical_cores: int | str
    max_clock_mhz: int | str
    socket: str  # e.g. "BGA1440" (soldered), "LGA1200", "AM4", or "Unknown"


@dataclass
class RAMInfo:
    """Installed RAM capacity, slot usage, speed, and generation."""

    total_gb: float | str
    slots_used: int | str
    speed_mhz: int | str
    ram_type: str


@dataclass
class GPUInfo:
    """Primary GPU name, reported VRAM, and adapter type."""

    name: str
    vram_gb: float | str
    gpu_type: str  # "Integrated", "Dedicated", or "Unknown"


@dataclass
class MotherboardInfo:
    """Motherboard manufacturer, product model, and full OEM system product name."""

    manufacturer: str
    model: str
    system_model: str  # Win32_ComputerSystemProduct.Name — may carry variant suffix


@dataclass
class StorageInfo:
    """Physical storage device name, capacity, and drive type."""

    name: str
    size_gb: float | str
    drive_type: str  # e.g. "NVMe SSD", "SATA SSD", "SATA HDD", "ATA HDD", "Unknown"


@dataclass
class WiFiInfo:
    """Primary WiFi network adapter name."""

    name: str  # e.g. "Intel(R) Wi-Fi 6 AX200 160MHz" or "Unknown"


@dataclass
class SystemInfo:
    """Operating-system and machine-type metadata relevant to upgrade planning."""

    os_name: str          # e.g. "Windows 11 Home" (Caption without "Microsoft ")
    os_version: str       # e.g. "10.0.26200"
    os_build: str         # e.g. "26200"
    os_install_date: str  # "YYYY-MM-DD" from Win32_OperatingSystem.InstallDate; proxy for purchase
    system_type: str      # "Laptop", "Desktop", "Workstation", or "Unknown"


@dataclass
class PowerInfo:
    """Battery health snapshot. has_battery=False means no battery was detected
    (typically a desktop, but also a laptop with the battery removed or a UPS-less rig)."""

    battery_name: str        # Win32_Battery.Name or "Unknown"
    design_capacity_mwh: int | str   # original capacity in mWh; "Unknown" if unavailable
    full_charge_capacity_mwh: int | str  # current max charge in mWh; "Unknown" if unavailable
    health_pct: int | str    # (full_charge / design) * 100, rounded; "Unknown" if unavailable
    has_battery: bool        # True when Win32_Battery returned at least one battery


@dataclass
class HardwareSpecs:
    """Complete hardware snapshot of the local machine."""

    cpu: CPUInfo
    ram: RAMInfo
    gpu: GPUInfo
    motherboard: MotherboardInfo
    drives: list[StorageInfo]
    wifi: WiFiInfo
    power: PowerInfo
    system: SystemInfo


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


def _is_integrated_gpu(name: str | None) -> bool:
    """Return True if the GPU name matches known integrated graphics patterns."""
    if not name:
        return False
    lower = name.lower()
    return any(kw in lower for kw in _INTEGRATED_GPU_KEYWORDS)


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
    """Extract CPU name, core counts, max clock speed, and socket via WMI and psutil."""
    name: str = "Unknown"
    max_clock: int | str = "Unknown"
    socket: str = "Unknown"
    try:
        proc = wmi.WMI().Win32_Processor()[0]
        name = proc.Name.strip() if proc.Name else "Unknown"
        max_clock = int(proc.MaxClockSpeed) if proc.MaxClockSpeed else "Unknown"
        socket = (proc.SocketDesignation or "").strip() or "Unknown"
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
        socket=socket,
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
    """Extract GPU name, VRAM, and type via WMI, preferring registry for accurate VRAM.

    Filters out virtual display adapters (Microsoft Basic, RDP, Citrix, VM
    adapters). Dedicated GPUs are preferred over integrated ones; among
    candidates the highest VRAM wins. WMI AdapterRAM is unreliable (32-bit
    DWORD overflow), so registry is the primary VRAM source; AdapterRAM is
    only a last-resort fallback.
    """
    name: str = "Unknown"
    vram_gb: float | str = "Unknown"
    gpu_type: str = "Unknown"
    try:
        all_controllers = wmi.WMI().Win32_VideoController()
        controllers = [g for g in all_controllers if _is_real_gpu(g.Name)]
        if not controllers:
            return GPUInfo(name=name, vram_gb=vram_gb, gpu_type=gpu_type)

        scored: list[tuple[float, str, str]] = []  # (vram, name, gpu_type)
        for g in controllers:
            g_name = g.Name.strip() if g.Name else "Unknown"
            reg_vram = _vram_from_registry(g_name)
            if isinstance(reg_vram, float):
                vram = reg_vram
            else:
                raw_bytes = _adapter_ram_to_bytes(g.AdapterRAM)
                vram = round(raw_bytes / (1024**3), 1) if raw_bytes > 0 else 0.0
            gtype = "Integrated" if _is_integrated_gpu(g_name) else "Dedicated"
            scored.append((vram, g_name, gtype))

        # Prefer dedicated GPUs; fall back to highest-VRAM integrated if none.
        dedicated = [(v, n, t) for v, n, t in scored if t == "Dedicated"]
        candidates = dedicated if dedicated else scored
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_vram, best_name, best_type = candidates[0]
        name = best_name
        vram_gb = best_vram if best_vram > 0 else "Unknown"
        gpu_type = best_type
    except Exception:
        pass

    return GPUInfo(name=name, vram_gb=vram_gb, gpu_type=gpu_type)


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


def _get_drives() -> list[StorageInfo]:
    """Extract physical storage devices via MSFT_PhysicalDisk, falling back to Win32_DiskDrive.

    Primary source is MSFT_PhysicalDisk (root/microsoft/windows/storage namespace),
    which correctly reports MediaType (SSD/HDD) and BusType (NVMe/SATA/ATA).
    Removable drives (USB, SD, MMC) are excluded. Falls back to Win32_DiskDrive
    for drive name and size only when the primary source is unavailable.
    """
    drives: list[StorageInfo] = []

    try:
        storage_wmi = wmi.WMI(namespace="root/microsoft/windows/storage")
        for disk in storage_wmi.MSFT_PhysicalDisk():
            try:
                bus_type = int(disk.BusType or 0)
            except (TypeError, ValueError):
                bus_type = 0
            if bus_type in _REMOVABLE_BUS_TYPES:
                continue

            try:
                media_type = int(disk.MediaType or 0)
            except (TypeError, ValueError):
                media_type = 0

            name = _clean_board_string(disk.FriendlyName)

            try:
                size_gb: float | str = round(int(disk.Size) / (1024**3), 1)
            except (TypeError, ValueError):
                size_gb = "Unknown"

            bus_label = _BUS_TYPE_NAMES.get(bus_type, "")
            media_label = _MEDIA_TYPE_NAMES.get(media_type, "")
            if bus_label and media_label:
                drive_type = f"{bus_label} {media_label}"
            elif media_label:
                drive_type = media_label
            else:
                drive_type = "Unknown"

            drives.append(StorageInfo(name=name, size_gb=size_gb, drive_type=drive_type))

        if drives:
            return drives
    except Exception:
        pass

    # Fallback: Win32_DiskDrive — drive type detection is unreliable here,
    # but at least returns name and size for all fixed drives.
    try:
        for disk in wmi.WMI().Win32_DiskDrive():
            if (disk.InterfaceType or "").strip().upper() == "USB":
                continue
            name = _clean_board_string(disk.Model)
            try:
                size_gb = round(int(disk.Size) / (1024**3), 1)
            except (TypeError, ValueError):
                size_gb = "Unknown"
            drives.append(StorageInfo(name=name, size_gb=size_gb, drive_type="Unknown"))
    except Exception:
        pass

    return drives


def _is_real_wifi(name: str | None, adapter_type: str | None) -> bool:
    """Return True for a physical WiFi adapter, False for virtual or Bluetooth-only entries."""
    if not name:
        return False
    name_lower = name.lower()
    if any(v in name_lower for v in _VIRTUAL_WIFI_KEYWORDS):
        return False
    type_lower = (adapter_type or "").lower()
    return "802.11" in type_lower or any(kw in name_lower for kw in _WIFI_KEYWORDS)


def _get_wifi() -> WiFiInfo:
    """Extract the primary physical WiFi adapter name via Win32_NetworkAdapter.

    Picks the first adapter where AdapterType contains '802.11' or the name
    contains a recognised WiFi keyword. Virtual adapters (Microsoft Wi-Fi Direct,
    hosted network, Bluetooth-only entries) are excluded.
    """
    name: str = "Unknown"
    try:
        for adapter in wmi.WMI().Win32_NetworkAdapter():
            if not adapter.PhysicalAdapter:
                continue
            if _is_real_wifi(adapter.Name, adapter.AdapterType):
                name = (adapter.Name or "").strip() or "Unknown"
                break
    except Exception:
        pass
    return WiFiInfo(name=name)


def _get_power() -> PowerInfo:
    """Extract battery health via WMI; returns has_battery=False when no battery is detected.

    Primary source: root/WMI BatteryStaticData (design capacity) and
    BatteryFullChargedCapacity (current max capacity), both in mWh.
    Battery presence is detected via Win32_Battery; no entry means no battery
    (typically a desktop).
    """
    has_battery = False
    battery_name: str = "Unknown"
    design_mwh: int | str = "Unknown"
    full_mwh: int | str = "Unknown"
    health_pct: int | str = "Unknown"

    try:
        batteries = wmi.WMI().Win32_Battery()
        if batteries:
            has_battery = True
            battery_name = _clean_board_string(batteries[0].Name)
    except Exception:
        pass

    if has_battery:
        try:
            root_wmi = wmi.WMI(namespace="root/WMI")
            static = root_wmi.BatteryStaticData()
            full = root_wmi.BatteryFullChargedCapacity()
            if static:
                design_mwh = int(static[0].DesignedCapacity)
            if full:
                full_mwh = int(full[0].FullChargedCapacity)
            if isinstance(design_mwh, int) and isinstance(full_mwh, int) and design_mwh > 0:
                health_pct = round((full_mwh / design_mwh) * 100)
        except Exception:
            pass

    return PowerInfo(
        battery_name=battery_name,
        design_capacity_mwh=design_mwh,
        full_charge_capacity_mwh=full_mwh,
        health_pct=health_pct,
        has_battery=has_battery,
    )


def _parse_wmi_date(wmi_date: str | None) -> str:
    """Parse a WMI DMTF datetime string (YYYYMMDDHHMMSS.mmmmmm+UUU) to YYYY-MM-DD.

    Returns 'Unknown' when the input is absent or malformed.
    """
    if not wmi_date or len(wmi_date) < 8:
        return "Unknown"
    try:
        return f"{wmi_date[:4]}-{wmi_date[4:6]}-{wmi_date[6:8]}"
    except Exception:
        return "Unknown"


def _get_system_info() -> SystemInfo:
    """Extract OS name, version, build, install date, and PC form factor via WMI.

    OS info comes from Win32_OperatingSystem; form factor from
    Win32_ComputerSystem.PCSystemType. The install date is the best available
    proxy for the machine's age — it resets on OS reinstalls, not on purchase.
    """
    os_name: str = "Unknown"
    os_version: str = "Unknown"
    os_build: str = "Unknown"
    os_install_date: str = "Unknown"
    system_type: str = "Unknown"

    try:
        os_obj = wmi.WMI().Win32_OperatingSystem()[0]
        caption = (os_obj.Caption or "").strip()
        os_name = caption.replace("Microsoft ", "").strip() or "Unknown"
        os_version = (os_obj.Version or "Unknown").strip()
        os_build = str(os_obj.BuildNumber or "Unknown").strip()
        os_install_date = _parse_wmi_date(os_obj.InstallDate)
    except Exception:
        pass

    try:
        cs = wmi.WMI().Win32_ComputerSystem()[0]
        pc_type = int(cs.PCSystemType or 0)
        system_type = _PC_SYSTEM_TYPES.get(pc_type, "Unknown")
    except Exception:
        pass

    return SystemInfo(
        os_name=os_name,
        os_version=os_version,
        os_build=os_build,
        os_install_date=os_install_date,
        system_type=system_type,
    )


def collect() -> HardwareSpecs:
    """Collect all hardware specs from this machine and return a HardwareSpecs instance."""
    return HardwareSpecs(
        cpu=_get_cpu(),
        ram=_get_ram(),
        gpu=_get_gpu(),
        motherboard=_get_motherboard(),
        drives=_get_drives(),
        wifi=_get_wifi(),
        power=_get_power(),
        system=_get_system_info(),
    )
