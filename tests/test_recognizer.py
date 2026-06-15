from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw

from tomato_freshness import TomatoFreshnessRecognizer


class TomatoFreshnessRecognizerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.recognizer = TomatoFreshnessRecognizer()

    def _make_image(self, path: Path, fill: str, spot: bool = False) -> None:
        image = Image.new("RGB", (360, 260), "#f5f5f0")
        draw = ImageDraw.Draw(image)
        draw.ellipse((80, 35, 285, 230), fill=fill, outline="#8f1d1d", width=3)
        draw.ellipse((135, 70, 175, 105), fill="#ffb0a0")
        if spot:
            draw.ellipse((155, 135, 230, 205), fill="#241814")
        image.save(path)

    def test_excellent_tomato_can_be_recognized(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "excellent.png"
            self._make_image(image_path, "#d92323")
            result = self.recognizer.recognize(image_path)
            self.assertTrue(result.success)
            self.assertIn(result.fresh_level, {"优质", "新鲜合格"})

    def test_rotten_tomato_triggers_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "rotten.png"
            self._make_image(image_path, "#8d3127", spot=True)
            result = self.recognizer.recognize(image_path)
            self.assertTrue(result.success)
            self.assertTrue(result.is_abnormal)
            self.assertIn(result.fresh_level, {"轻微变质", "严重变质"})


if __name__ == "__main__":
    unittest.main()
