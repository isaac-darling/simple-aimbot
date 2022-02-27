# November 2021
# Use `ctypes` module to call windows c functions

from ctypes import POINTER, WINFUNCTYPE, windll
from ctypes.wintypes import BOOL, HWND, RECT

prototype = WINFUNCTYPE(BOOL, HWND, POINTER(RECT))
paramflags = (1, "hwnd"), (2, "lprect")
get_client_rect = prototype(("ClientToScreen", windll.user32), paramflags)

def GetClientPosition(window_handle: int) -> tuple[int, int]:
    """Finds the top-left corner of the window content using ClientToScreen from user32.dll"""
    rect = get_client_rect(window_handle)
    return rect.left, rect.top
