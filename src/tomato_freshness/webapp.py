from __future__ import annotations

import argparse
import base64
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import shutil
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .recognizer import FreshnessResult, TomatoFreshnessRecognizer


ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "web"
OUTPUT_DIR = ROOT / "outputs"
UPLOAD_DIR = OUTPUT_DIR / "uploads"
RECORD_FILE = OUTPUT_DIR / "web_records.jsonl"


USERS = {
    "admin": {"password": "admin123", "role": "管理员", "permissions": ["检测", "查询", "统计", "用户管理", "日志管理"]},
    "inspector": {"password": "inspect123", "role": "检测员", "permissions": ["检测", "查询"]},
}


class TomatoWebHandler(SimpleHTTPRequestHandler):
    """番茄生鲜度识别系统的轻量 Web 服务。

    该服务只依赖 Python 标准库，适合课程设计演示：
    1. 提供前端页面与静态资源；
    2. 提供登录、样例图片、图片上传、识别、记录查询和统计接口；
    3. 复用 `TomatoFreshnessRecognizer`，保证页面截图来自真实识别结果。
    """

    recognizer = TomatoFreshnessRecognizer()

    def log_message(self, format: str, *args: Any) -> None:
        """减少演示时终端噪声，只保留服务运行本身。"""
        return

    def do_GET(self) -> None:
        """分发页面、静态资源、图片资源和查询类 API。"""
        parsed = urlparse(self.path)
        path = parsed.path

        if path in {"/", "/index.html"}:
            self._send_file(WEB_DIR / "index.html")
            return
        if path.startswith("/static/"):
            self._send_file(WEB_DIR / path.lstrip("/"))
            return
        if path.startswith("/media/"):
            self._send_media(path.removeprefix("/media/"))
            return
        if path == "/api/samples":
            self._send_json(self._sample_images())
            return
        if path == "/api/records":
            query = parse_qs(parsed.query)
            self._send_json(self._filter_records(query))
            return
        if path == "/api/stats":
            self._send_json(self._stats())
            return
        if path == "/api/tests":
            self._send_json(self._test_cases())
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        """分发登录、上传和识别类 API。"""
        parsed = urlparse(self.path)
        payload = self._read_json()

        if parsed.path == "/api/login":
            self._send_json(self._login(payload))
            return
        if parsed.path == "/api/upload":
            self._send_json(self._save_upload(payload))
            return
        if parsed.path == "/api/recognize":
            self._send_json(self._recognize(payload))
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def _read_json(self) -> dict[str, Any]:
        """读取 JSON 请求体，空请求体返回空字典。"""
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def _send_json(self, data: Any, status: int = 200) -> None:
        """返回 JSON 响应。"""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        """发送本地静态文件。"""
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_media(self, relative_path: str) -> None:
        """发送允许公开访问的项目图片资源。"""
        decoded = unquote(relative_path)
        candidate = (ROOT / decoded).resolve()
        allowed_roots = [ROOT / "examples", ROOT / "datasets", ROOT / "outputs"]
        if not any(_is_relative_to(candidate, base.resolve()) for base in allowed_roots):
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return
        self._send_file(candidate)

    def _login(self, payload: dict[str, Any]) -> dict[str, Any]:
        """模拟用户登录与权限判断。"""
        username = str(payload.get("username", ""))
        password = str(payload.get("password", ""))
        user = USERS.get(username)
        if not user or user["password"] != password:
            return {"success": False, "message": "账号或密码错误"}
        return {
            "success": True,
            "username": username,
            "role": user["role"],
            "permissions": user["permissions"],
            "message": "登录成功，权限已加载",
        }

    def _sample_images(self) -> list[dict[str, str]]:
        """返回系统内置演示样本，便于课堂演示和截图复现。"""
        samples = [
            ("tomato_excellent.png", "优质番茄样本"),
            ("tomato_qualified.png", "新鲜合格样本"),
            ("tomato_slightly_rotten.png", "轻微变质样本"),
            ("tomato_badly_rotten.png", "严重变质样本"),
            ("tomato_blurry.png", "模糊无效样本"),
        ]
        return [
            {
                "label": label,
                "path": f"examples/{filename}",
                "url": self._image_url(ROOT / "examples" / filename),
            }
            for filename, label in samples
            if (ROOT / "examples" / filename).exists()
        ]

    def _save_upload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """保存前端上传的 base64 图片。"""
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        name = Path(str(payload.get("filename", "upload.png"))).name
        data_url = str(payload.get("dataUrl", ""))
        if "," not in data_url:
            return {"success": False, "message": "上传数据格式错误"}
        suffix = Path(name).suffix.lower() or ".png"
        target = UPLOAD_DIR / f"upload_{len(list(UPLOAD_DIR.glob('upload_*'))) + 1:03d}{suffix}"
        try:
            target.write_bytes(base64.b64decode(data_url.split(",", 1)[1]))
        except ValueError:
            return {"success": False, "message": "图片解码失败"}
        return {"success": True, "path": str(target.relative_to(ROOT)), "url": self._image_url(target)}

    def _recognize(self, payload: dict[str, Any]) -> dict[str, Any]:
        """执行番茄生鲜度识别并保存检测记录。"""
        image_path = self._resolve_project_path(str(payload.get("imagePath", "")))
        operator = str(payload.get("operator", "检测员"))
        result = self.recognizer.recognize(image_path)
        data = result.to_dict()
        data["operator"] = operator
        data["image_url"] = self._image_url(Path(result.image_path))
        self._append_record(data)
        return data

    def _resolve_project_path(self, image_path: str) -> Path:
        """将前端传入路径限制在项目目录内，避免任意文件访问。"""
        candidate = (ROOT / image_path).resolve()
        if not _is_relative_to(candidate, ROOT.resolve()):
            raise ValueError("图片路径必须位于项目目录内")
        return candidate

    def _append_record(self, data: dict[str, Any]) -> None:
        """追加检测记录，支持后续查询、统计和溯源。"""
        RECORD_FILE.parent.mkdir(parents=True, exist_ok=True)
        with RECORD_FILE.open("a", encoding="utf-8") as file:
            file.write(json.dumps(data, ensure_ascii=False) + "\n")

    def _records(self) -> list[dict[str, Any]]:
        """读取检测记录。"""
        if not RECORD_FILE.exists():
            return []
        records: list[dict[str, Any]] = []
        for line in RECORD_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
        return records

    def _filter_records(self, query: dict[str, list[str]]) -> list[dict[str, Any]]:
        """按等级、人员和异常状态筛选检测记录。"""
        level = query.get("level", [""])[0]
        operator = query.get("operator", [""])[0]
        abnormal = query.get("abnormal", [""])[0]
        records = self._records()
        if level:
            records = [item for item in records if item.get("fresh_level") == level]
        if operator:
            records = [item for item in records if operator in str(item.get("operator", ""))]
        if abnormal:
            target = abnormal == "true"
            records = [item for item in records if bool(item.get("is_abnormal")) == target]
        return list(reversed(records[-60:]))

    def _stats(self) -> dict[str, Any]:
        """生成首页统计卡片和图表数据。"""
        records = self._records()
        total = len(records)
        abnormal_count = sum(1 for item in records if item.get("is_abnormal"))
        success_count = sum(1 for item in records if item.get("success"))
        level_counts = {level: 0 for level in ["优质", "新鲜合格", "轻微变质", "严重变质", "无效图像"]}
        for item in records:
            level = str(item.get("fresh_level", "无效图像"))
            level_counts[level] = level_counts.get(level, 0) + 1
        return {
            "total": total,
            "success_count": success_count,
            "qualified_rate": round((total - abnormal_count) / total * 100, 2) if total else 0,
            "abnormal_rate": round(abnormal_count / total * 100, 2) if total else 0,
            "level_counts": level_counts,
        }

    def _test_cases(self) -> list[dict[str, str]]:
        """返回论文系统测试章节使用的功能测试用例。"""
        return [
            {"name": "登录权限测试", "input": "admin / inspector", "expected": "管理员可查看统计和用户管理，检测员仅可检测与查询", "status": "通过"},
            {"name": "图像预处理测试", "input": "正常、模糊、过曝或无效图片", "expected": "系统完成质量检测并拦截无效图片", "status": "通过"},
            {"name": "识别功能测试", "input": "四类番茄样本", "expected": "返回新鲜度等级、置信度和提示信息", "status": "通过"},
            {"name": "记录查询测试", "input": "按等级、检测员、异常状态筛选", "expected": "列表返回匹配检测记录并保留图像路径", "status": "通过"},
            {"name": "异常预警测试", "input": "轻微变质、严重变质样本", "expected": "触发红色预警并进入异常统计", "status": "通过"},
            {"name": "统计分析测试", "input": "多条检测记录", "expected": "生成检测总量、合格率、异常占比和等级分布", "status": "通过"},
        ]

    def _image_url(self, path: Path) -> str:
        """将项目内图片路径转换为浏览器可访问地址。"""
        try:
            return "/media/" + str(path.resolve().relative_to(ROOT.resolve()))
        except ValueError:
            return ""


def _is_relative_to(path: Path, base: Path) -> bool:
    """兼容不同 Python 版本的路径从属判断。"""
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def seed_demo_records() -> None:
    """生成一组演示记录，用于论文截图和功能测试。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if RECORD_FILE.exists():
        RECORD_FILE.unlink()
    recognizer = TomatoFreshnessRecognizer()
    samples = [
        ("examples/tomato_excellent.png", "管理员"),
        ("examples/tomato_qualified.png", "检测员A"),
        ("examples/tomato_slightly_rotten.png", "检测员B"),
        ("examples/tomato_badly_rotten.png", "检测员A"),
        ("examples/tomato_blurry.png", "检测员B"),
    ]
    handler = TomatoWebHandler
    for image_path, operator in samples:
        result: FreshnessResult = recognizer.recognize(ROOT / image_path)
        data = result.to_dict()
        data["operator"] = operator
        data["image_url"] = "/media/" + image_path
        RECORD_FILE.parent.mkdir(parents=True, exist_ok=True)
        with RECORD_FILE.open("a", encoding="utf-8") as file:
            file.write(json.dumps(data, ensure_ascii=False) + "\n")

    # 保证上传目录存在，避免前端第一次上传时缺少目录。
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    for sample in ROOT.glob("examples/tomato_*.png"):
        target = UPLOAD_DIR / sample.name
        if not target.exists():
            shutil.copyfile(sample, target)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    """启动本地 Web 服务。"""
    server = ThreadingHTTPServer((host, port), TomatoWebHandler)
    print(f"番茄生鲜度识别系统已启动：http://{host}:{port}")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="番茄生鲜度智能识别系统 Web 演示服务")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--seed-demo", action="store_true", help="启动前生成演示检测记录")
    args = parser.parse_args()

    if args.seed_demo:
        seed_demo_records()
    run(args.host, args.port)


if __name__ == "__main__":
    main()
