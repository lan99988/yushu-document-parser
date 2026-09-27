from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from document_parser_mcp.local import LocalMinerUBackend


class LocalBackendTests(unittest.TestCase):
    def test_invokes_pipeline_with_exact_paths_language_and_returns_artifacts(self):
        calls: list[list[str]] = []

        def runner(command, **kwargs):
            calls.append(command)
            output = Path(command[command.index("-o") + 1])
            parsed = output / "中文 样例" / "pipeline" / "auto"
            parsed.mkdir(parents=True)
            (parsed / "中文 样例.md").write_text("# 本机解析", encoding="utf-8")
            (parsed / "中文 样例_content_list.json").write_text("[]", encoding="utf-8")
            (parsed / "images").mkdir()
            (parsed / "images" / "图.png").write_bytes(b"image")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "中文 样例.pdf"
            source.write_bytes(b"pdf")
            output = Path(temporary) / "结果 输出"
            result = LocalMinerUBackend(runner=runner).parse_file(source, output, language="en")

            self.assertEqual(calls[0][calls[0].index("-p") + 1], str(source.resolve()))
            self.assertEqual(calls[0][calls[0].index("-o") + 1], str(output.resolve()))
            self.assertEqual(calls[0][-6:], ["-b", "pipeline", "-m", "auto", "-l", "en"])
            self.assertTrue(Path(result["markdown_path"]).is_file())
            self.assertTrue(Path(result["content_list_path"]).is_file())
            self.assertEqual([Path(path).name for path in result["image_paths"]], ["图.png"])

    def test_nonzero_mineru_exit_is_reported_as_failure(self):
        def runner(command, **kwargs):
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="模型加载失败")

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "broken.pdf"
            source.write_bytes(b"pdf")
            with self.assertRaisesRegex(RuntimeError, "模型加载失败"):
                LocalMinerUBackend(runner=runner).parse_file(source, Path(temporary) / "out")


if __name__ == "__main__":
    unittest.main()
