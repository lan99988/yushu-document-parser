from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import httpx

from document_parser_mcp.remote import RemoteMinerUBackend


def result_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipped:
        zipped.writestr("中文 报告.md", "# 解析完成\n正文")
        zipped.writestr("中文 报告_content_list.json", '[{"type":"text"}]')
        zipped.writestr("images/图表.png", b"png-bytes")
    return buffer.getvalue()


class RemoteBackendTests(unittest.TestCase):
    def test_uploads_polls_downloads_zip_and_saves_consistent_artifacts(self):
        events: list[str] = []
        status_calls = 0
        expected_zip = result_zip()

        def handle(request: httpx.Request) -> httpx.Response:
            nonlocal status_calls
            events.append(f"{request.method} {request.url.path}")
            if request.method == "POST" and request.url.path == "/tasks":
                body = request.read()
                self.assertIn("中文 报告.pdf".encode(), body)
                self.assertIn(b"return_content_list", body)
                return httpx.Response(202, json={"task_id": "task-1"})
            if request.method == "GET" and request.url.path == "/tasks/task-1":
                status_calls += 1
                state = "pending" if status_calls == 1 else "completed"
                return httpx.Response(200, json={"task_id": "task-1", "status": state})
            if request.method == "GET" and request.url.path == "/tasks/task-1/result":
                return httpx.Response(200, content=expected_zip, headers={"content-type": "application/zip"})
            return httpx.Response(404)

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "中文 报告.pdf"
            source.write_bytes(b"pdf-bytes")
            output = Path(temporary) / "output"
            output.mkdir()
            backend = RemoteMinerUBackend(
                "http://mineru.tailnet:8000",
                poll_interval=0,
                max_wait_seconds=2,
                transport=httpx.MockTransport(handle),
            )

            result = backend.parse_file(source, output, language="ch")

            self.assertEqual(result["status"], "success")
            self.assertEqual(Path(result["markdown_path"]).read_text(encoding="utf-8"), "# 解析完成\n正文")
            self.assertTrue(Path(result["content_list_path"]).is_file())
            self.assertEqual([Path(item).name for item in result["image_paths"]], ["图表.png"])
            self.assertEqual(status_calls, 2)
            self.assertEqual(events, ["POST /tasks", "GET /tasks/task-1", "GET /tasks/task-1", "GET /tasks/task-1/result"])


if __name__ == "__main__":
    unittest.main()
