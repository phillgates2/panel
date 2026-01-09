import io
import random
import subprocess
from typing import Optional

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont  # type: ignore

    _HAVE_PIL = True
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    ImageFilter = None  # type: ignore
    ImageFont = None  # type: ignore
    _HAVE_PIL = False


def _random_text(n=6):
    # Exclude confusing characters: 0, O, I, 1, L for better readability
    choices = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(random.choice(choices) for _ in range(n))


def _png_bytes_from_rgba(w: int, h: int, rgba: bytes) -> bytes:
    import struct
    import zlib

    if len(rgba) != w * h * 4:
        raise ValueError("Invalid RGBA buffer size")

    # PNG scanlines: each row is prefixed with filter byte 0
    row_bytes = w * 4
    raw = bytearray((row_bytes + 1) * h)
    for y in range(h):
        raw[y * (row_bytes + 1)] = 0
        start = y * row_bytes
        raw[y * (row_bytes + 1) + 1 : y * (row_bytes + 1) + 1 + row_bytes] = rgba[
            start : start + row_bytes
        ]

    comp = zlib.compress(bytes(raw), level=6)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp) + chunk(b"IEND", b"")


def _generate_fallback_captcha_png(text: str) -> bytes:
    # Dependency-free captcha renderer. Uses a simple 7-segment style for digits.
    # In fallback mode we stick to digits only for reliable rendering.
    w, h = 250, 80
    pixels = bytearray([255, 255, 255, 255]) * (w * h)

    def set_px(x: int, y: int, r: int, g: int, b: int, a: int = 255) -> None:
        if 0 <= x < w and 0 <= y < h:
            i = (y * w + x) * 4
            pixels[i : i + 4] = bytes((r, g, b, a))

    def fill_rect(x: int, y: int, rw: int, rh: int, r: int, g: int, b: int) -> None:
        for yy in range(y, y + rh):
            for xx in range(x, x + rw):
                set_px(xx, yy, r, g, b)

    seg_map = {
        "2": "abged",
        "3": "abgcd",
        "4": "fgbc",
        "5": "afgcd",
        "6": "afgcde",
        "7": "abc",
        "8": "abcdefg",
        "9": "abfgcd",
    }

    def draw_digit(x0: int, y0: int, digit: str, scale: int = 3) -> None:
        # Segment rectangles in a 7-seg layout.
        # a: top, b: upper-right, c: lower-right, d: bottom, e: lower-left, f: upper-left, g: middle
        t = max(1, scale)  # thickness
        dw = 8 * scale
        dh = 14 * scale
        # segment coords: (x, y, width, height)
        segs = {
            "a": (x0 + t, y0, dw - 2 * t, t),
            "d": (x0 + t, y0 + dh - t, dw - 2 * t, t),
            "g": (x0 + t, y0 + dh // 2 - t // 2, dw - 2 * t, t),
            "f": (x0, y0 + t, t, dh // 2 - t),
            "e": (x0, y0 + dh // 2, t, dh // 2 - t),
            "b": (x0 + dw - t, y0 + t, t, dh // 2 - t),
            "c": (x0 + dw - t, y0 + dh // 2, t, dh // 2 - t),
        }

        active = seg_map.get(digit, "")
        for seg in active:
            rx, ry, rw, rh = segs[seg]
            fill_rect(rx, ry, rw, rh, 0, 0, 0)

    # Draw faint noise
    for _ in range(220):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        v = random.randint(170, 230)
        set_px(x, y, v, v, v)

    # Render digits centered
    digit_scale = 3
    per_w = 8 * digit_scale
    gap = 6
    total_w = len(text) * per_w + (len(text) - 1) * gap
    x = (w - total_w) // 2
    y = (h - 14 * digit_scale) // 2
    for ch in text:
        draw_digit(x, y + random.randint(-2, 2), ch, scale=digit_scale)
        x += per_w + gap

    return _png_bytes_from_rgba(w, h, bytes(pixels))


def _random_text_fallback(n: int = 6) -> str:
    # Digits-only fallback (guaranteed renderable without Pillow).
    choices = "23456789"
    return "".join(random.choice(choices) for _ in range(n))


def generate_captcha_image(length=6):
    if _HAVE_PIL:
        text = _random_text(length)
        width = 250
        height = 80

        image = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        except Exception:
            try:
                font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()

        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except Exception:
            tw, th = draw.textsize(text, font=font)

        x = (width - tw) // 2
        y = (height - th) // 2

        draw.text((x, y), text, font=font, fill=(0, 0, 0))

        # Light noise
        for _ in range(30):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            draw.line((x1, y1, x2, y2), fill=(180, 180, 180), width=1)

        image = image.filter(ImageFilter.SMOOTH)
        image = image.filter(ImageFilter.SHARPEN)

        bio = io.BytesIO()
        image.save(bio, format="PNG")
        generate_captcha_image._last_image = bio.getvalue()
        return text

    # Fallback: generate digits-only captcha without Pillow
    text = _random_text_fallback(length)
    generate_captcha_image._last_image = _generate_fallback_captcha_png(text)
    return text


def generate_captcha_audio(text=None):
    # Prefer system espeak when available, otherwise fall back to a simple
    # tone-based WAV that still gives audible feedback for each character.
    if text is None:
        text = generate_captcha_image()

    text = str(text)

    if supports_audio():
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmpname = tmp.name
        try:
            subprocess.run(["espeak", "-w", tmpname, text], check=True)
            with open(tmpname, "rb") as f:
                data = f.read()
            return data
        finally:
            try:
                import os

                os.unlink(tmpname)
            except Exception:
                pass

    # Pure-Python fallback WAV generator
    import math
    import wave

    sample_rate = 8000
    tone_ms = 220
    gap_ms = 80
    amplitude = 12000

    def char_freq(ch: str) -> int:
        # Map characters to distinct tones.
        # Keep within speech-ish range so it's audible.
        base = 440
        if ch.isdigit():
            return 350 + int(ch) * 35
        if ch.isalpha():
            return base + ((ord(ch.upper()) - 65) % 12) * 35
        return 500

    frames = bytearray()
    for ch in text:
        freq = char_freq(ch)
        n = int(sample_rate * (tone_ms / 1000.0))
        for i in range(n):
            v = int(amplitude * math.sin(2.0 * math.pi * freq * (i / sample_rate)))
            frames += int(v).to_bytes(2, byteorder="little", signed=True)
        gap = int(sample_rate * (gap_ms / 1000.0))
        frames += (0).to_bytes(2, byteorder="little", signed=True) * gap

    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))
    return bio.getvalue()


# Provide helper to retrieve last image bytes (used by app)
def last_image_bytes():
    return getattr(generate_captcha_image, "_last_image", None)


def supports_audio() -> bool:
    # espeak is optional; this just hints whether audio generation is likely to work.
    import shutil

    return shutil.which("espeak") is not None
