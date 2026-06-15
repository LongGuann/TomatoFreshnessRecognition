from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "examples"


def draw_tomato(path: Path, fill: str, spots: list[tuple[int, int, int, str]] | None = None, blur: bool = False) -> None:
    """生成番茄演示图片，用于验证识别流程是否可以正常运行。"""
    image = Image.new("RGB", (420, 320), "#f7f7f2")
    draw = ImageDraw.Draw(image)

    # 番茄主体。
    draw.ellipse((90, 45, 335, 285), fill=fill, outline="#8f1d1d", width=4)

    # 叶柄区域。
    draw.polygon([(205, 45), (225, 18), (240, 55), (270, 35), (250, 72)], fill="#2f7d32")

    # 高光，增强普通图片的真实感。
    draw.ellipse((150, 85, 205, 125), fill="#ffb0a0")

    for x, y, r, color in spots or []:
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color)

    if blur:
        image = image.filter(ImageFilter.GaussianBlur(radius=5))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    image.save(path)


def main() -> None:
    draw_tomato(OUT_DIR / "tomato_excellent.png", "#d92323")
    draw_tomato(OUT_DIR / "tomato_qualified.png", "#d4552f", [(250, 190, 16, "#8c4a2d")])
    draw_tomato(
        OUT_DIR / "tomato_slightly_rotten.png",
        "#bd3a28",
        [(180, 185, 32, "#4a2f21"), (260, 150, 22, "#5b3824")],
    )
    draw_tomato(
        OUT_DIR / "tomato_badly_rotten.png",
        "#8d3127",
        [(160, 170, 48, "#211715"), (245, 185, 55, "#251b16"), (220, 105, 30, "#3a241a")],
    )
    draw_tomato(OUT_DIR / "tomato_blurry.png", "#d92323", blur=True)
    print(f"演示图片已生成：{OUT_DIR}")


if __name__ == "__main__":
    main()
