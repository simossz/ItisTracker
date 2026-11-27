from pathlib import Path

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def draw_logo(size):
    scale = size / 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = 2 * scale
    radius = 14 * scale
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=radius,
        fill=(23, 23, 21, 255),
    )

    left, top, right, bottom = 16 * scale, 16 * scale, 48 * scale, 48 * scale
    width = max(1, round(2.6 * scale))
    draw.line([(left, 32 * scale), (right, 32 * scale)], fill=(255, 255, 255, 255), width=width)
    draw.line([(32 * scale, top), (32 * scale, bottom)], fill=(255, 255, 255, 255), width=width)

    r = 4 * scale
    draw.ellipse(
        [32 * scale - r, 32 * scale - r, 32 * scale + r, 32 * scale + r],
        fill=(23, 23, 21, 255),
        outline=(255, 255, 255, 255),
        width=max(1, round(2.2 * scale)),
    )
    return img


def build():
    output = PROJECT_ROOT
    for size, name in ((32, "favicon.png"), (180, "apple-touch-icon.png"), (512, "logo.png")):
        draw_logo(size).save(output / name)

    master = draw_logo(64)
    master.save(output / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print("icone generate")


if __name__ == "__main__":
    build()
