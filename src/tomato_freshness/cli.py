from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .recognizer import TomatoFreshnessRecognizer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="番茄生鲜度智能识别命令行工具")
    parser.add_argument("image", help="待识别的番茄图片路径")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出完整识别结果")
    parser.add_argument("--record", help="将识别结果追加保存到 JSONL 记录文件")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    recognizer = TomatoFreshnessRecognizer()
    result = recognizer.recognize(Path(args.image))

    if args.record:
        recognizer.save_record(result, args.record)

    if args.json:
        print(result.to_json())
    else:
        print(f"图片路径：{result.image_path}")
        print(f"识别状态：{'成功' if result.success else '失败'}")
        print(f"生鲜品类：{result.category}")
        print(f"新鲜度等级：{result.fresh_level}")
        print(f"新鲜度得分：{result.freshness_score}")
        print(f"置信度：{result.confidence}")
        print(f"异常状态：{'异常' if result.is_abnormal else '正常'}")
        print(f"提示信息：{result.warning}")
        print(f"系统消息：{result.message}")

    return 0 if result.success else 2


if __name__ == "__main__":
    sys.exit(main())
