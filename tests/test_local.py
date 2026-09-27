from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from document_parser_mcp.local import LocalMinerUBackend


class FakeWriter:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)


class FakeResult:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def save(self, writer: FakeWriter) -> None:
        self.assert_writer(writer)
        writer.output_dir.mkdir(parents=True, exist_ok=True)
        (writer.output_dir / "markdown.md").write_text("# 本机解析", encoding="utf-8")
        (writer.output_dir / "structured_content.json").write_text('{"pages": []}', encoding="utf-8")
        (writer.output_dir / "middle_json.json").write_text('{"pages": []}', encoding="utf-8")
        images = writer.output_dir / "images"
        images.mkdir()
        (images / "figure.png").write_bytes(b"image")

    def assert_writer(self, writer: FakeWriter) -> None:
        if writer.output_dir != self.output_dir:
            raise AssertionError("MinerU writer received the wrong output directory")


class LocalBackendTests(unittest.TestCase):
    def test_calls_mineru_4_sdk_with_selected_tier_and_saves_v4_artifacts(self):
        calls: list[tuple[str, str]] = []

        def parse(path: str, *, tier: str):
            calls.append((path, tier))
            return FakeResult(Path(output_dir))

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "中文 报告.rtf"
            source.write_bytes(b"rtf")
            output_dir = str(Path(temporary) / "结果 输出")
            result = LocalMinerUBackend(parser=parse, writer_factory=FakeWriter).parse_file(
                source, Path(output_dir), tier="flash"
            )

            self.assertEqual(calls, [(str(source.resolve()), "flash")])
            self.assertTrue(Path(result["markdown_path"]).is_file())
            self.assertTrue(Path(result["structured_content_path"]).is_file())
            self.assertTrue(Path(result["middle_json_path"]).is_file())
            self.assertEqual([Path(path).name for path in result["image_paths"]], ["figure.png"])

    def test_mineru_sdk_errors_are_reported(self):
        def parse(path: str, *, tier: str):
            raise RuntimeError("模型加载失败")

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "broken.pdf"
            source.write_bytes(b"pdf")
            backend = LocalMinerUBackend(parser=parse, writer_factory=FakeWriter)
            with self.assertRaisesRegex(RuntimeError, "模型加载失败"):
                backend.parse_file(source, Path(temporary) / "out", tier="standard")


if __name__ == "__main__":
    unittest.main()
