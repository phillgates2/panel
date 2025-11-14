import random
import string
import io
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def _random_text(n=6):
    choices = string.ascii_uppercase + string.digits
    return "".join(random.choice(choices) for _ in range(n))


def generate_captcha_image(length=6):
    text = _random_text(length)
    # create simple image
    width = 200
    height = 70
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
    except Exception:
        font = ImageFont.load_default()

    # draw text centered with random small offset
    w, h = draw.textsize(text, font=font)
    x = (width - w) // 2
    y = (height - h) // 2
    draw.text((x, y), text, font=font, fill=(0, 0, 0))
    # add noise lines
    for i in range(6):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line(((x1, y1), (x2, y2)), fill=(0, 0, 0), width=1)

    image = image.filter(ImageFilter.SMOOTH)

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
