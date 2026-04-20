"""GDI-based screen capture helper. Returns PNG-encoded bytes."""

import ctypes
import struct
import zlib
from ctypes import wintypes

# GDI constants
SRCCOPY = 0x00CC0020
BI_RGB = 0
DIB_RGB_COLORS = 0


def capture_rect(x, y, width, height):
    """Capture a rectangle from the virtual screen and return PNG bytes.

    Args:
        x, y: Top-left corner in physical screen pixels.
        width, height: Size in physical pixels.

    Returns:
        bytes: A PNG file, or b"" on failure.
    """
    if width <= 0 or height <= 0:
        return b""

    gdi32 = ctypes.windll.gdi32
    user32 = ctypes.windll.user32

    # Get a DC for the entire virtual screen.
    hdc_screen = user32.GetDC(None)
    if not hdc_screen:
        return b""

    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    hbm = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
    old_bm = gdi32.SelectObject(hdc_mem, hbm)

    # Copy from screen to our memory bitmap.
    gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, x, y, SRCCOPY)

    # Read pixel data via GetDIBits (24-bit BGR, bottom-up).
    bmi = _make_bitmapinfo(width, height)
    row_stride = (width * 3 + 3) & ~3  # 24-bit rows padded to 4 bytes
    buf_size = row_stride * height
    pixel_buf = (ctypes.c_ubyte * buf_size)()

    gdi32.GetDIBits(
        hdc_mem, hbm, 0, height, pixel_buf, ctypes.byref(bmi), DIB_RGB_COLORS
    )

    # Clean up GDI resources.
    gdi32.SelectObject(hdc_mem, old_bm)
    gdi32.DeleteObject(hbm)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(None, hdc_screen)

    # Convert BGR bottom-up to RGB top-down and encode as PNG.
    return _bgr_to_png(pixel_buf, width, height, row_stride)


def _bgr_to_png(bgr_data, width, height, row_stride):
    """Encode bottom-up BGR pixel data as a PNG file."""
    # Build raw image data for PNG: each row is prefixed with filter byte 0 (None).
    raw_rows = bytearray()
    for y in range(height):
        # Bottom-up: row 0 in GDI is the bottom row.
        src_offset = (height - 1 - y) * row_stride
        raw_rows.append(0)  # PNG filter: None
        for x in range(width):
            px = src_offset + x * 3
            b = bgr_data[px]
            g = bgr_data[px + 1]
            r = bgr_data[px + 2]
            raw_rows.extend((r, g, b))

    # Compress with zlib (deflate).
    compressed = zlib.compress(bytes(raw_rows))

    # Build PNG file.
    chunks = []

    # IHDR chunk
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    chunks.append(_png_chunk(b"IHDR", ihdr_data))

    # IDAT chunk(s)
    chunks.append(_png_chunk(b"IDAT", compressed))

    # IEND chunk
    chunks.append(_png_chunk(b"IEND", b""))

    return b"\x89PNG\r\n\x1a\n" + b"".join(chunks)


def _png_chunk(chunk_type, data):
    """Build a single PNG chunk with CRC."""
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class _BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", _BITMAPINFOHEADER),
    ]


def _make_bitmapinfo(width, height):
    """Create a BITMAPINFO struct for 24-bit RGB capture."""
    bmi = _BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = height  # positive = bottom-up (for GetDIBits)
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 24
    bmi.bmiHeader.biCompression = BI_RGB
    return bmi
