from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from document_parser_mcp.artifacts import allocate_output_dir, safe_extract_zip


class ArtifactTests(unittest.TestCase):
    def test_output_directory_preserves_chinese_spaces_and_never_reuses_existing_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "解析结果"
            source = Path(temporary) / "输入 文件" / "中文 样例.pdf"
            source.parent.mkdir()
            source.write_bytes(b"sample")

            first = allocate_output_dir(root, source)
            second = allocate_output_dir(root, source)

            self.assertEqual(first.name, "中文 样例")
            self.assertEqual(second.name, "中文 样例-2")
            self.assertTrue(first.is_dir())
            self.assertTrue(second.is_dir())

    def test_zip_extraction_rejects_path_traversal_before_writing_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "result.zip"
            destination = root / "output"
            destination.mkdir()
            with zipfile.ZipFile(archive, "w") as zipped:
                zipped.writestr("safe.md", "ok")
                zipped.writestr("../../outside.txt", "unsafe")

            with self.assertRaises(ValueError):
                safe_extract_zip(archive, destination)

            self.assertFalse((root.parent / "outside.txt").exists())
            self.assertFalse((destination / "safe.md").exists())


if __name__ == "__main__":
    unittest.main()
