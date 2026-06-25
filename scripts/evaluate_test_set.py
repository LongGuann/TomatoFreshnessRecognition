from __future__ import annotations

import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from tomato_freshness import TomatoFreshnessRecognizer


ROOT = Path(__file__).resolve().parents[1]
LABEL_FILE = ROOT / "datasets" / "test_set" / "labels.csv"
EVAL_DIR = ROOT / "docs" / "evaluation"
PREDICTION_FILE = EVAL_DIR / "predictions.csv"
SUMMARY_FILE = EVAL_DIR / "summary_metrics.json"
CONFUSION_CHART = EVAL_DIR / "confusion_matrix.png"
DISTRIBUTION_CHART = EVAL_DIR / "prediction_distribution.png"
SCORE_CHART = EVAL_DIR / "average_score_by_class.png"

LEVELS = ["优质", "新鲜合格", "轻微变质", "严重变质"]


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """加载中文字体；若系统字体不可用，则回退到 Pillow 默认字体。"""
    for font_path in [
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
    ]:
        path = Path(font_path)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def read_labels() -> list[dict[str, str]]:
    """读取测试集标签文件。"""
    with LABEL_FILE.open("r", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def evaluate() -> tuple[list[dict[str, str]], dict[str, object]]:
    """批量运行识别器并计算汇总指标。"""
    recognizer = TomatoFreshnessRecognizer()
    labels = read_labels()
    predictions: list[dict[str, str]] = []

    confusion = {true: {pred: 0 for pred in LEVELS} for true in LEVELS}
    score_bucket = {level: [] for level in LEVELS}
    correct = 0

    for row in labels:
        image_path = ROOT / row["image_path"]
        result = recognizer.recognize(image_path)
        predicted = result.fresh_level if result.fresh_level in LEVELS else "严重变质"
        true_label = row["label"]

        if true_label in confusion:
            confusion[true_label][predicted] += 1
            score_bucket[true_label].append(result.freshness_score)
        if predicted == true_label:
            correct += 1

        predictions.append(
            {
                "image_path": row["image_path"],
                "true_label": true_label,
                "predicted_label": predicted,
                "success": str(result.success),
                "freshness_score": f"{result.freshness_score:.2f}",
                "confidence": f"{result.confidence:.4f}",
                "is_abnormal": str(result.is_abnormal),
                "warning": result.warning,
                "red_ratio": f"{result.features.get('red_ratio', 0):.4f}",
                "dark_spot_ratio": f"{result.features.get('dark_spot_ratio', 0):.4f}",
                "brown_ratio": f"{result.features.get('brown_ratio', 0):.4f}",
            }
        )

    total = len(predictions)
    per_class_accuracy = {}
    for level in LEVELS:
        level_total = sum(confusion[level].values())
        per_class_accuracy[level] = round(confusion[level][level] / level_total, 4) if level_total else 0

    summary = {
        "dataset": str(LABEL_FILE.relative_to(ROOT)),
        "sample_count": total,
        "overall_accuracy": round(correct / total, 4) if total else 0,
        "per_class_accuracy": per_class_accuracy,
        "confusion_matrix": confusion,
        "average_score_by_true_class": {
            level: round(sum(values) / len(values), 2) if values else 0 for level, values in score_bucket.items()
        },
    }
    return predictions, summary


def save_predictions(predictions: list[dict[str, str]]) -> None:
    """保存每张测试图片的预测明细。"""
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    with PREDICTION_FILE.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(predictions[0].keys()))
        writer.writeheader()
        writer.writerows(predictions)


def save_summary(summary: dict[str, object]) -> None:
    """保存评估指标 JSON。"""
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    with SUMMARY_FILE.open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)


def draw_confusion_matrix(summary: dict[str, object]) -> None:
    """绘制混淆矩阵图。"""
    confusion = summary["confusion_matrix"]  # type: ignore[index]
    image = Image.new("RGB", (1300, 900), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_font(38)
    text_font = load_font(25)
    small_font = load_font(23)

    draw.text((420, 35), "番茄生鲜度识别混淆矩阵", fill="#111827", font=title_font)
    left, top = 290, 205
    cell_w, cell_h = 210, 120

    draw.text((80, 455), "真实等级", fill="#111827", font=text_font)
    draw.text((655, 112), "预测等级", fill="#111827", font=text_font)

    for i, level in enumerate(LEVELS):
        draw.text((left + i * cell_w + 72, top - 45), level, fill="#111827", font=small_font)
        draw.text((left - 145, top + i * cell_h + 43), level, fill="#111827", font=small_font)

    max_value = max(max(row.values()) for row in confusion.values()) or 1
    for row_index, true_level in enumerate(LEVELS):
        for col_index, pred_level in enumerate(LEVELS):
            value = confusion[true_level][pred_level]
            intensity = int(245 - (value / max_value) * 120)
            fill = (intensity, 230, 255) if true_level == pred_level else (255, intensity, intensity)
            x1 = left + col_index * cell_w
            y1 = top + row_index * cell_h
            x2 = x1 + cell_w
            y2 = y1 + cell_h
            draw.rectangle((x1, y1, x2, y2), fill=fill, outline="#334155", width=2)
            draw.text((x1 + 95, y1 + 43), str(value), fill="#111827", font=text_font)

    image.save(CONFUSION_CHART)


def draw_distribution_chart(predictions: list[dict[str, str]]) -> None:
    """绘制预测等级分布柱状图。"""
    counts = {level: 0 for level in LEVELS}
    for row in predictions:
        counts[row["predicted_label"]] += 1

    image = Image.new("RGB", (1000, 720), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_font(38)
    text_font = load_font(25)
    small_font = load_font(22)

    draw.text((315, 35), "预测等级分布图", fill="#111827", font=title_font)
    left, bottom = 120, 610
    bar_w = 120
    max_count = max(counts.values()) or 1

    draw.line((left, 120, left, bottom), fill="#334155", width=3)
    draw.line((left, bottom, 920, bottom), fill="#334155", width=3)

    colors = ["#22C55E", "#84CC16", "#F59E0B", "#EF4444"]
    for index, level in enumerate(LEVELS):
        height = int((counts[level] / max_count) * 390)
        x1 = left + 95 + index * 190
        y1 = bottom - height
        x2 = x1 + bar_w
        draw.rectangle((x1, y1, x2, bottom), fill=colors[index], outline="#334155", width=2)
        draw.text((x1 + 42, y1 - 35), str(counts[level]), fill="#111827", font=text_font)
        draw.text((x1 - 20, bottom + 25), level, fill="#111827", font=small_font)

    image.save(DISTRIBUTION_CHART)


def draw_score_chart(summary: dict[str, object]) -> None:
    """绘制各真实等级平均新鲜度得分图。"""
    scores = summary["average_score_by_true_class"]  # type: ignore[index]
    image = Image.new("RGB", (1000, 720), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_font(38)
    text_font = load_font(25)
    small_font = load_font(22)

    draw.text((245, 35), "各等级平均新鲜度得分", fill="#111827", font=title_font)
    left, bottom = 120, 610
    draw.line((left, 120, left, bottom), fill="#334155", width=3)
    draw.line((left, bottom, 920, bottom), fill="#334155", width=3)

    for score in [0, 25, 50, 75, 100]:
        y = bottom - int(score / 100 * 430)
        draw.line((left - 8, y, 920, y), fill="#E5E7EB", width=1)
        draw.text((55, y - 12), str(score), fill="#475569", font=small_font)

    colors = ["#22C55E", "#84CC16", "#F59E0B", "#EF4444"]
    for index, level in enumerate(LEVELS):
        value = float(scores[level])
        height = int(value / 100 * 430)
        x1 = left + 95 + index * 190
        y1 = bottom - height
        x2 = x1 + 120
        draw.rectangle((x1, y1, x2, bottom), fill=colors[index], outline="#334155", width=2)
        draw.text((x1 + 20, y1 - 35), f"{value:.1f}", fill="#111827", font=text_font)
        draw.text((x1 - 20, bottom + 25), level, fill="#111827", font=small_font)

    image.save(SCORE_CHART)


def main() -> None:
    predictions, summary = evaluate()
    save_predictions(predictions)
    save_summary(summary)
    draw_confusion_matrix(summary)
    draw_distribution_chart(predictions)
    draw_score_chart(summary)

    print(f"预测明细：{PREDICTION_FILE}")
    print(f"汇总指标：{SUMMARY_FILE}")
    print(f"混淆矩阵：{CONFUSION_CHART}")
    print(f"预测分布：{DISTRIBUTION_CHART}")
    print(f"平均得分：{SCORE_CHART}")
    print(f"总体准确率：{summary['overall_accuracy']}")


if __name__ == "__main__":
    main()
