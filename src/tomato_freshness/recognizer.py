from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError


LEVELS = ("优质", "新鲜合格", "轻微变质", "严重变质")


@dataclass
class ImageQuality:
    """图像质量检测结果。"""

    valid: bool
    message: str
    brightness: float
    contrast: float
    sharpness: float
    tomato_ratio: float


@dataclass
class FreshnessResult:
    """单张番茄图片的识别结果。"""

    success: bool
    image_path: str
    category: str
    fresh_level: str
    confidence: float
    freshness_score: float
    is_abnormal: bool
    warning: str
    message: str
    features: dict[str, float]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class TomatoFreshnessRecognizer:
    """基于图像启发式规则的番茄生鲜度识别器。

    当前版本不依赖训练模型，主要用于课程设计演示：
    1. 读取图片并统一为 RGB；
    2. 依据红色/橙色像素粗略分割番茄区域；
    3. 计算颜色成熟度、暗斑比例、绿色比例和纹理边缘强度；
    4. 根据规则输出优质、新鲜合格、轻微变质、严重变质四类结果。

    后续如果接入 CNN 模型，可以保留 `recognize()` 的返回结构不变，
    只替换 `_score_freshness()` 的内部实现。
    """

    def __init__(self, image_size: int = 224) -> None:
        self.image_size = image_size

    def recognize(self, image_path: str | Path) -> FreshnessResult:
        """识别单张番茄图片并返回结构化结果。"""
        path = Path(image_path)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            image = self._load_image(path)
            array = self._preprocess(image)
            tomato_mask = self._build_tomato_mask(array)
            quality = self._check_quality(array, tomato_mask)
        except (FileNotFoundError, UnidentifiedImageError, ValueError) as exc:
            return FreshnessResult(
                success=False,
                image_path=str(path),
                category="番茄",
                fresh_level="无法识别",
                confidence=0.0,
                freshness_score=0.0,
                is_abnormal=True,
                warning="图片读取失败，无法完成识别",
                message=str(exc),
                features={},
                created_at=created_at,
            )

        features = self._extract_features(array, tomato_mask, quality)

        if not quality.valid:
            return FreshnessResult(
                success=False,
                image_path=str(path),
                category="番茄",
                fresh_level="无效图像",
                confidence=0.0,
                freshness_score=0.0,
                is_abnormal=True,
                warning="请重新采集番茄图片",
                message=quality.message,
                features=features,
                created_at=created_at,
            )

        score = self._score_freshness(features)
        level = self._level_from_score(score)
        confidence = self._confidence_from_score(score, features)
        is_abnormal = level in {"轻微变质", "严重变质"}
        warning = self._build_warning(level)

        return FreshnessResult(
            success=True,
            image_path=str(path),
            category="番茄",
            fresh_level=level,
            confidence=confidence,
            freshness_score=round(score, 2),
            is_abnormal=is_abnormal,
            warning=warning,
            message="识别完成",
            features=features,
            created_at=created_at,
        )

    def save_record(self, result: FreshnessResult, record_path: str | Path) -> None:
        """将检测结果以 JSON Lines 形式追加保存，便于后续溯源查询。"""
        path = Path(record_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")

    def _load_image(self, path: Path) -> Image.Image:
        """读取图片并处理 EXIF 方向，避免手机照片旋转错误。"""
        if not path.exists():
            raise FileNotFoundError(f"图片不存在：{path}")
        image = Image.open(path)
        return ImageOps.exif_transpose(image).convert("RGB")

    def _preprocess(self, image: Image.Image) -> np.ndarray:
        """统一尺寸并归一化到 0-1 浮点数组。"""
        resized = image.resize((self.image_size, self.image_size))
        return np.asarray(resized, dtype=np.float32) / 255.0

    def _build_tomato_mask(self, array: np.ndarray) -> np.ndarray:
        """依据红、橙、黄绿色像素粗略定位番茄主体区域。"""
        red = array[:, :, 0]
        green = array[:, :, 1]
        blue = array[:, :, 2]

        # 红/橙色番茄：R 通道明显占优。
        red_or_orange = (red > 0.35) & (red > green * 1.08) & (red > blue * 1.15)

        # 未完全成熟的番茄可能偏黄绿，因此保留一部分黄绿色区域。
        yellow_green = (red > 0.25) & (green > 0.25) & (blue < 0.35) & (red + green > blue * 2.4)

        # 暗斑区域也属于番茄主体，避免腐烂斑点被背景排除。
        brightness = self._grayscale(array)
        dark_tomato_like = (brightness < 0.32) & (red > blue * 0.8) & (green > blue * 0.65)

        return red_or_orange | yellow_green | dark_tomato_like

    def _check_quality(self, array: np.ndarray, tomato_mask: np.ndarray) -> ImageQuality:
        """检测图片是否满足最低识别质量要求。"""
        gray = self._grayscale(array)
        brightness = float(gray.mean())
        contrast = float(gray.std())
        sharpness = self._sharpness(gray)
        tomato_ratio = float(tomato_mask.mean())

        if tomato_ratio < 0.03:
            return ImageQuality(False, "未检测到明显番茄区域", brightness, contrast, sharpness, tomato_ratio)
        if brightness < 0.08:
            return ImageQuality(False, "图像过暗，请改善光照后重新采集", brightness, contrast, sharpness, tomato_ratio)
        if brightness > 0.92:
            return ImageQuality(False, "图像过曝，请重新采集", brightness, contrast, sharpness, tomato_ratio)
        if contrast < 0.025:
            return ImageQuality(False, "图像对比度过低，无法可靠识别", brightness, contrast, sharpness, tomato_ratio)
        if sharpness < 0.002:
            return ImageQuality(False, "图像过于模糊，请重新拍摄", brightness, contrast, sharpness, tomato_ratio)

        return ImageQuality(True, "图像质量合格", brightness, contrast, sharpness, tomato_ratio)

    def _extract_features(
        self,
        array: np.ndarray,
        tomato_mask: np.ndarray,
        quality: ImageQuality,
    ) -> dict[str, float]:
        """提取用于评分的颜色、暗斑和纹理特征。"""
        red = array[:, :, 0]
        green = array[:, :, 1]
        blue = array[:, :, 2]
        gray = self._grayscale(array)

        if tomato_mask.any():
            tomato_pixels = array[tomato_mask]
            tomato_gray = gray[tomato_mask]
            red_pixels = tomato_pixels[:, 0]
            green_pixels = tomato_pixels[:, 1]
            blue_pixels = tomato_pixels[:, 2]
        else:
            tomato_gray = gray.reshape(-1)
            red_pixels = red.reshape(-1)
            green_pixels = green.reshape(-1)
            blue_pixels = blue.reshape(-1)

        red_ratio = float(((red_pixels > green_pixels * 1.12) & (red_pixels > blue_pixels * 1.18)).mean())
        green_ratio = float(((green_pixels > red_pixels * 0.92) & (green_pixels > blue_pixels * 1.25)).mean())
        dark_spot_ratio = float((tomato_gray < 0.22).mean())

        # 棕褐色近似：整体偏暗、红色不再鲜亮、绿红比例接近褐色区域。
        # 这里避免把正常高饱和红色番茄误判为棕褐斑点。
        tomato_brightness = tomato_gray
        brown_ratio = float(
            (
                (tomato_brightness < 0.48)
                & (red_pixels > 0.16)
                & (red_pixels < 0.68)
                & (green_pixels / np.maximum(red_pixels, 0.001) > 0.34)
                & (blue_pixels < 0.28)
            ).mean()
        )
        edge_score = self._masked_edge_score(gray, tomato_mask)

        return {
            "brightness": round(quality.brightness, 4),
            "contrast": round(quality.contrast, 4),
            "sharpness": round(quality.sharpness, 4),
            "tomato_ratio": round(quality.tomato_ratio, 4),
            "red_ratio": round(red_ratio, 4),
            "green_ratio": round(green_ratio, 4),
            "dark_spot_ratio": round(dark_spot_ratio, 4),
            "brown_ratio": round(brown_ratio, 4),
            "edge_score": round(edge_score, 4),
        }

    def _score_freshness(self, features: dict[str, float]) -> float:
        """根据启发式规则计算 0-100 分的新鲜度分值。"""
        score = 100.0

        # 红色占比越高，通常代表成熟且外观较好；红色不足时扣分。
        score -= max(0.0, 0.72 - features["red_ratio"]) * 28

        # 绿色比例过高可能代表未成熟或颜色异常。
        score -= features["green_ratio"] * 18

        # 暗斑和棕褐区域是变质、压伤、腐烂的主要视觉依据。
        score -= features["dark_spot_ratio"] * 220
        score -= features["brown_ratio"] * 110

        # 边缘纹理过强时，可能存在皱缩、裂纹或复杂斑点。
        score -= max(0.0, features["edge_score"] - 0.07) * 120

        # 光照和对比度轻微影响评分，但不作为主要依据。
        score -= abs(features["brightness"] - 0.48) * 8
        score -= max(0.0, 0.08 - features["contrast"]) * 30

        return float(min(100.0, max(0.0, score)))

    def _level_from_score(self, score: float) -> str:
        """将新鲜度分值映射到论文中的四个等级。"""
        if score >= 85:
            return "优质"
        if score >= 70:
            return "新鲜合格"
        if score >= 50:
            return "轻微变质"
        return "严重变质"

    def _confidence_from_score(self, score: float, features: dict[str, float]) -> float:
        """生成演示用置信度，数值反映规则判断的明确程度。"""
        boundaries = [50, 70, 85]
        distance = min(abs(score - boundary) for boundary in boundaries)
        confidence = 0.58 + min(distance / 35, 1.0) * 0.28
        confidence += min(features["tomato_ratio"], 0.4) * 0.18
        return round(float(min(0.96, max(0.50, confidence))), 4)

    def _build_warning(self, level: str) -> str:
        """根据等级生成异常预警文案。"""
        if level == "轻微变质":
            return "发现轻微变质番茄，建议复检或降级处理"
        if level == "严重变质":
            return "发现严重变质番茄，建议立即下架处理"
        return "番茄质量正常"

    def _grayscale(self, array: np.ndarray) -> np.ndarray:
        """按人眼感知权重计算灰度图。"""
        return array[:, :, 0] * 0.299 + array[:, :, 1] * 0.587 + array[:, :, 2] * 0.114

    def _sharpness(self, gray: np.ndarray) -> float:
        """使用相邻像素差分近似清晰度，避免依赖 OpenCV。"""
        dx = np.diff(gray, axis=1)
        dy = np.diff(gray, axis=0)
        return float(dx.var() + dy.var())

    def _masked_edge_score(self, gray: np.ndarray, mask: np.ndarray) -> float:
        """计算番茄区域内部的边缘/纹理强度。"""
        dx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
        dy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
        edge = dx + dy
        if mask.any():
            return float(edge[mask].mean())
        return float(edge.mean())
