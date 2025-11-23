import io
import random
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont


def _random_text(n=6):
    # Exclude confusing characters: 0, O, I, 1, L for better readability
    choices = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(random.choice(choices) for _ in range(n))


def generate_captcha_image(length=6):
    text = _random_text(length)
    # create image with enhanced quality for 900% zoom
    width = 250
    height = 40
    # Use white background for maximum contrast and quality
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Use 16px font optimized for 50x25 image with high quality
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
    except Exception:
        # Try to load a default font or use built-in with size parameter
        try:
            font = ImageFont.load_default(size=20)
        except Exception:
            font = ImageFont.load_default()

    # draw text centered with better positioning
    try:
        # Pillow >= 8: textbbox gives precise bbox
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
    except Exception:
        try:
            w, h = font.getsize(text)
        except Exception:
            # fallback to approximate sizes for 16px font in 50x25 image
            w = len(text) * 7
            h = 20
    x = (width - w) // 2
    y = (height - h) // 3

    # Draw text with maximum contrast (black on white)
    draw.text((x, y), text, font=font, fill=(0, 0, 0))

    # Skip noise lines for maximum text clarity in tiny image

    # Apply quality enhancement: smooth first, then sharpen for crisp text
    image = image.filter(ImageFilter.SMOOTH)
    image = image.filter(ImageFilter.SHARPEN)
    image = image.filter(ImageFilter.EDGE_ENHANCE)

    bio = io.BytesIO()
    image.save(bio, format="PNG")
    bio.seek(0)

    # store bytes in a place the app can return on request (app uses session)
    return_text = text
    # We return text but also provide image bytes via a dynamic mechanism used by app
    # For simplicity, return text and image bytes in a tuple-like global return
    # But to keep API simple, set an attribute
    generate_captcha_image._last_image = bio.getvalue()
    return return_text


def generate_captcha_audio(text=None):
    # Uses system espeak to synthesize audio locally.
    if text is None:
        text = generate_captcha_image()
    # synthesize wav to stdout
    # espeak -w - "text" will write to filename; we'll use a temp file approach
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmpname = tmp.name
    try:
        subprocess.run(["espeak", "-w", tmpname, text], check=True)
        with open(tmpname, "rb") as f:
            data = f.read()
    finally:
        try:
            import os

            os.unlink(tmpname)
        except Exception:
            pass
    return data


# Provide helper to retrieve last image bytes (used by app)
def last_image_bytes():
    return getattr(generate_captcha_image, "_last_image", None)
