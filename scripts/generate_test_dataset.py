from __future__ import annotations

import csv
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "datasets" / "test_set"
LABEL_FILE = DATASET_DIR / "labels.csv"

LEVEL_CONFIG = {
    "excellent": {
        "label": "优质",
        "base_colors": ["#d92323", "#e02b24", "#cf2424"],
        "spot_count": (0, 1),
        "spot_radius": (5, 10),
        "spot_colors": ["#a52b24", "#b7352a"],
    },
    "qualified": {
        "label": "新鲜合格",
        "base_colors": ["#d4552f", "#c9472d", "#d86a38"],
        "spot_count": (1, 2),
        "spot_radius": (10, 18),
        "spot_colors": ["#8c4a2d", "#7f3c2c"],
    },
    "slightly_rotten": {
        "label": "轻微变质",
        "base_colors": ["#bd3a28", "#ad3427", "#a83a2a"],
        "spot_count": (2, 4),
        "spot_radius": (22, 36),
        "spot_colors": ["#4a2f21", "#5b3824", "#3f2a21"],
    },
    "badly_rotten": {
        "label": "严重变质",
        "base_colors": ["#8d3127", "#7f2c25", "#793026"],
        "spot_count": (4, 6),
        "spot_radius": (32, 58),
        "spot_colors": ["#211715", "#251b16", "#3a241a"],
    },
}


def draw_sample(path: Path, config: dict[str, object], index: int, rng: random.Random) -> None:
    """根据等级配置生成一张带轻微随机扰动的番茄测试图片。"""
    image = Image.new("RGB", (420, 320), rng.choice(["#f7f7f2", "#f1f2ec", "#faf7ef"]))
    draw = ImageDraw.Draw(image)

    x_offset = rng.randint(-10, 10)
    y_offset = rng.randint(-6, 8)
    bbox = (88 + x_offset, 45 + y_offset, 336 + x_offset, 286 + y_offset)
    fill = rng.choice(config["base_colors"])  # type: ignore[index]

    draw.ellipse(bbox, fill=fill, outline="#8f1d1d", width=3)
    draw.polygon(
        [
            (205 + x_offset, 48 + y_offset),
            (225 + x_offset, 18 + y_offset),
            (240 + x_offset, 56 + y_offset),
            (270 + x_offset, 35 + y_offset),
            (250 + x_offset, 72 + y_offset),
        ],
        fill=rng.choice(["#2f7d32", "#3a8a3a", "#296d2c"]),
    )

    # 添加高光区域，使测试图片更接近普通拍摄图。
    highlight = (
        145 + x_offset + rng.randint(-5, 5),
        78 + y_offset + rng.randint(-4, 4),
        205 + x_offset + rng.randint(-5, 5),
        122 + y_offset + rng.randint(-4, 4),
    )
    draw.ellipse(highlight, fill=rng.choice(["#ffb0a0", "#f5a08f", "#ffc0b0"]))

    count_min, count_max = config["spot_count"]  # type: ignore[index]
    radius_min, radius_max = config["spot_radius"]  # type: ignore[index]
    for _ in range(rng.randint(count_min, count_max)):
        x = rng.randint(135, 270) + x_offset
        y = rng.randint(105, 220) + y_offset
        radius = rng.randint(radius_min, radius_max)
        color = rng.choice(config["spot_colors"])  # type: ignore[index]
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

    # 个别样本加入轻微模糊或暗角，模拟现场拍摄差异。
    if index % 5 == 0:
        image = image.filter(ImageFilter.GaussianBlur(radius=0.8))
    if index % 7 == 0:
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle((0, 0, 420, 320), fill=(0, 0, 0, 18))
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def main() -> None:
    rng = random.Random(20260625)
    rows: list[dict[str, str]] = []
    samples_per_level = 12

    for slug, config in LEVEL_CONFIG.items():
        level_dir = DATASET_DIR / slug
        for index in range(1, samples_per_level + 1):
            filename = f"{slug}_{index:02d}.png"
            image_path = level_dir / filename
            draw_sample(image_path, config, index, rng)
            rows.append(
                {
                    "image_path": str(image_path.relative_to(ROOT)),
                    "label": str(config["label"]),
                    "class_slug": slug,
                    "source": "synthetic",
                }
            )

    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    with LABEL_FILE.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["image_path", "label", "class_slug", "source"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"测试集已生成：{DATASET_DIR}")
    print(f"标签文件：{LABEL_FILE}")
    print(f"样本数量：{len(rows)}")


if __name__ == "__main__":
    main()
