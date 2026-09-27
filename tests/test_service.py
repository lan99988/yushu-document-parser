from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from document_parser_mcp.service import ParserService, SUPPORTED_EXTENSIONS


class WritingBackend:
    def __init__(self, failures: set[str] | None = None):
        self.failures = failures or set()
        self.calls: list[str] = []

    def parse_file(self, source: Path, output_dir: Path, language: str = "ch") -> dict:
        self.calls.append(source.name)
        if source.name in self.failures:
            raise RuntimeError("模拟解析失败")
        output_dir.mkdir(parents=True, exist_ok=True)
        markdown = output_dir / f"{source.stem}.md"
        markdown.write_text(f"解析：{source.name}\n第二行\n第三行", encoding="utf-8")
        content_list = output_dir / f"{source.stem}_content_list.json"
        content_list.write_text("[]", encoding="utf-8")
        return {"markdown_path": str(markdown), "content_list_path": str(content_list), "image_paths": []}


class ParserServiceTests(unittest.TestCase):
    def test_supports_required_document_types(self):
        self.assertEqual(
            SUPPORTED_EXTENSIONS,
            {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".docx", ".pptx", ".xlsx"},
        )

    def test_batch_reports_failure_and_continues_in_input_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = [root / name for name in ["甲.pdf", "坏.pdf", "乙.pdf"]]
            for file in files:
                file.write_bytes(b"sample")
            backend = WritingBackend({"坏.pdf"})
            service = ParserService(root / "outputs", {"local": backend})

            results = service.parse_many([str(file) for file in files])

            self.assertEqual([result["status"] for result in results], ["success", "error", "success"])
            self.assertEqual([result["input_path"] for result in results], [str(file.resolve()) for file in files])
            self.assertEqual(backend.calls, [file.name for file in files])
            self.assertIn("markdown_path", results[0])
            self.assertIn("preview", results[0])

    def test_read_text_returns_page_and_next_line(self):
        with tempfile.TemporaryDirectory() as temporary:
            markdown = Path(temporary) / "正文.md"
            markdown.write_text("一\n二\n三\n四\n", encoding="utf-8")
            service = ParserService(Path(temporary) / "outputs", {})

            result = service.read_text(str(markdown), start_line=2, max_lines=2)

            self.assertEqual(result["text"], "二\n三")
            self.assertEqual(result["start_line"], 2)
            self.assertEqual(result["next_line"], 4)
            self.assertTrue(result["has_more"])

    def test_explicit_unconfigured_remote_does_not_fall_back_to_local(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.pdf"
            source.write_bytes(b"pdf")
            local = WritingBackend()
            service = ParserService(root / "outputs", {"local": local})

            result = service.parse_one(str(source), backend="remote")

            self.assertEqual(result["status"], "error")
            self.assertEqual(local.calls, [])


if __name__ == "__main__":
    unittest.main()
