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
        zipped.writestr("markdown.md", "# 解析完成\n正文")
        zipped.writestr("structured_content.json", '{"pages": [{"page_idx": 0}]}')
        zipped.writestr("middle_json.json", '{"schema": "docvortex.middle"}')
        zipped.writestr("images/chart.png", b"png-bytes")
    return buffer.getvalue()


class RemoteBackendTests(unittest.TestCase):
    def test_v1_uploads_polls_downloads_zip_and_saves_consistent_artifacts(self):
        events: list[str] = []
        api_headers: list[dict[str, str]] = []
        uploaded: list[bytes] = []
        status_calls = 0
        expected_zip = result_zip()

        def handle(request: httpx.Request) -> httpx.Response:
            nonlocal status_calls
            events.append(f"{request.method} {request.url.path}")
            if request.url.path.startswith("/v1/"):
                api_headers.append(dict(request.headers))
            if request.method == "POST" and request.url.path == "/v1/uploads":
                payload = json.loads(request.read())
                self.assertEqual(payload["filename"], "中文 报告.pdf")
                self.assertEqual(payload["mime_type"], "application/pdf")
                self.assertEqual(payload["purpose"], "parse")
                self.assertEqual(len(payload["sha256sum"]), 64)
                return httpx.Response(
                    201,
                    json={
                        "id": "upload-1",
                        "status": "pending",
                        "upload_url": "http://mineru.tailnet:8000/v1/uploads/upload-1/content",
                        "upload_method": "PUT",
                        "upload_headers": {"X-Upload-Token": "local-upload"},
                    },
                )
            if request.method == "PUT" and request.url.path == "/v1/uploads/upload-1/content":
                uploaded.append(request.read())
                self.assertEqual(request.headers.get("x-upload-token"), "local-upload")
                self.assertEqual(request.headers.get("authorization"), "Bearer secret")
                return httpx.Response(200)
            if request.method == "POST" and request.url.path == "/v1/uploads/upload-1/complete":
                return httpx.Response(200, json={"status": "completed", "file": {"id": "file-1"}})
            if request.method == "POST" and request.url.path == "/v1/parse/jobs":
                payload = json.loads(request.read())
                self.assertEqual(payload["files"][0]["source"], {"type": "file_id", "file_id": "file-1"})
                self.assertEqual(payload["tier"], "standard")
                self.assertEqual(payload["output_formats"], ["zip"])
                return httpx.Response(202, json={"job_id": "job-1", "status": "queued"})
            if request.method == "GET" and request.url.path == "/v1/parse/jobs/job-1":
                status_calls += 1
                if status_calls == 1:
                    return httpx.Response(200, json={"job_id": "job-1", "status": "running", "files": []})
                return httpx.Response(
                    200,
                    json={
                        "job_id": "job-1",
                        "status": "completed",
                        "files": [
                            {
                                "name": "中文 报告.pdf",
                                "status": "completed",
                                "output_files": {"zip": {"file_id": "output-zip"}},
                            }
                        ],
                    },
                )
            if request.method == "GET" and request.url.path == "/v1/files/output-zip/content":
                return httpx.Response(200, content=expected_zip, headers={"content-type": "application/zip"})
            return httpx.Response(404)

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "中文 报告.pdf"
            source.write_bytes(b"pdf-bytes")
            output = Path(temporary) / "output"
            output.mkdir()
            backend = RemoteMinerUBackend(
                "http://mineru.tailnet:8000",
                token="secret",
                poll_interval=0,
                max_wait_seconds=2,
                transport=httpx.MockTransport(handle),
            )

            result = backend.parse_file(source, output, tier="standard")

            self.assertEqual(result["status"], "success")
            self.assertEqual(Path(result["markdown_path"]).read_text(encoding="utf-8"), "# 解析完成\n正文")
            self.assertTrue(Path(result["structured_content_path"]).is_file())
            self.assertTrue(Path(result["middle_json_path"]).is_file())
            self.assertEqual([Path(item).name for item in result["image_paths"]], ["chart.png"])
            self.assertEqual(uploaded, [b"pdf-bytes"])
            self.assertEqual(status_calls, 2)
            self.assertEqual(
                events,
                [
                    "POST /v1/uploads",
                    "PUT /v1/uploads/upload-1/content",
                    "POST /v1/uploads/upload-1/complete",
                    "POST /v1/parse/jobs",
                    "GET /v1/parse/jobs/job-1",
                    "GET /v1/parse/jobs/job-1",
                    "GET /v1/files/output-zip/content",
                ],
            )
            self.assertTrue(all(headers.get("authorization") == "Bearer secret" for headers in api_headers))

    def test_never_sends_api_token_to_cross_origin_presigned_upload_url(self):
        upload_headers: list[dict[str, str]] = []
        result_archive = result_zip()

        def handle(request: httpx.Request) -> httpx.Response:
            if request.method == "POST" and request.url.path == "/v1/uploads":
                return httpx.Response(
                    201,
                    json={
                        "id": "upload-1",
                        "status": "pending",
                        "upload_url": "https://storage.example/upload?signature=abc",
                        "upload_method": "PUT",
                        "upload_headers": {"X-Signed-Header": "signed"},
                    },
                )
            if request.method == "PUT" and request.url.host == "storage.example":
                upload_headers.append(dict(request.headers))
                return httpx.Response(200)
            if request.method == "POST" and request.url.path == "/v1/uploads/upload-1/complete":
                return httpx.Response(200, json={"status": "completed", "file": {"id": "file-1"}})
            if request.method == "POST" and request.url.path == "/v1/parse/jobs":
                return httpx.Response(202, json={"job_id": "job-1", "status": "completed", "files": [
                    {"name": "sample.pdf", "status": "completed", "output_files": {"zip": {"file_id": "output-zip"}}}
                ]})
            if request.method == "GET" and request.url.path == "/v1/files/output-zip/content":
                return httpx.Response(200, content=result_archive)
            return httpx.Response(404)

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "sample.pdf"
            source.write_bytes(b"pdf")
            backend = RemoteMinerUBackend(
                "https://mineru.tailnet:8000", token="sensitive-key", transport=httpx.MockTransport(handle)
            )
            backend.parse_file(source, Path(temporary) / "out", tier="standard")

        self.assertEqual(len(upload_headers), 1)
        self.assertNotIn("authorization", upload_headers[0])
        self.assertEqual(upload_headers[0].get("x-signed-header"), "signed")

    def test_never_sends_api_token_to_cross_origin_redirected_download(self):
        storage_headers: list[dict[str, str]] = []

        def handle(request: httpx.Request) -> httpx.Response:
            if request.method == "POST" and request.url.path == "/v1/uploads":
                return httpx.Response(200, json={"id": "upload-1", "status": "completed", "file": {"id": "file-1"}})
            if request.method == "POST" and request.url.path == "/v1/parse/jobs":
                return httpx.Response(202, json={"job_id": "job-1", "status": "completed", "files": [
                    {"name": "sample.pdf", "status": "completed", "output_files": {"zip": {"file_id": "output-zip"}}}
                ]})
            if request.method == "GET" and request.url.path == "/v1/files/output-zip/content":
                self.assertEqual(request.headers.get("authorization"), "Bearer sensitive-key")
                return httpx.Response(302, headers={"location": "https://storage.example/output.zip?signature=abc"})
            if request.method == "GET" and request.url.host == "storage.example":
                storage_headers.append(dict(request.headers))
                return httpx.Response(200, content=result_zip())
            return httpx.Response(404)

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "sample.pdf"
            source.write_bytes(b"pdf")
            backend = RemoteMinerUBackend(
                "https://mineru.tailnet:8000", token="sensitive-key", transport=httpx.MockTransport(handle)
            )
            result = backend.parse_file(source, Path(temporary) / "out", tier="standard")
            self.assertTrue(Path(result["markdown_path"]).is_file())
            self.assertEqual(len(storage_headers), 1)
            self.assertNotIn("authorization", storage_headers[0])


if __name__ == "__main__":
    unittest.main()
