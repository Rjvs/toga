import ctypes
from ctypes import wintypes
from functools import cached_property
from pathlib import Path

from toga import App


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_byte * 8),
    ]


# {F1B32785-6FBA-4FCF-9D55-7B8E7F157091}
FOLDERID_LocalAppData = _GUID(
    0xF1B32785,
    0x6FBA,
    0x4FCF,
    (ctypes.c_byte * 8)(0x9D, 0x55, 0x7B, 0x8E, 0x7F, 0x15, 0x70, 0x91),
)


def _get_local_app_data():
    """Resolve the LocalAppData folder using the Windows Shell API.

    Uses SHGetKnownFolderPath which correctly handles folder redirection
    and Group Policy in enterprise environments. Falls back to the
    conventional path if the API call fails.
    """
    try:
        path_ptr = ctypes.c_void_p()
        hr = ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(FOLDERID_LocalAppData),
            0,  # dwFlags
            None,  # hToken (current user)
            ctypes.byref(path_ptr),
        )
        if hr == 0:  # S_OK
            result = Path(ctypes.wstring_at(path_ptr.value))
            ctypes.windll.ole32.CoTaskMemFree(path_ptr)
            return result
    except Exception:
        pass
    return Path.home() / "AppData" / "Local"


class Paths:
    def __init__(self, interface):
        self.interface = interface

    @cached_property
    def _app_dir(self):
        author = "Unknown" if App.app.author is None else App.app.author
        return _get_local_app_data() / author / App.app.formal_name

    def get_config_path(self):
        return self._app_dir / "Config"

    def get_data_path(self):
        return self._app_dir / "Data"

    def get_cache_path(self):
        return self._app_dir / "Cache"

    def get_logs_path(self):
        return self._app_dir / "Logs"
