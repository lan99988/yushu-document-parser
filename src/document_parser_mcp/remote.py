from __future__ import annotations

import httpx
import os
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

from .artifacts import find_artifacts, safe_extract_zip


class RemoteMinerUBackend:
    """Send a document to an explicitly configured MinerU API and save its ZIP locally."""

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        poll_interval: float = 2.0,
        max_wait_seconds: float = 1800.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.poll_interval = max(0.0, poll_interval)
        self.max_wait_seconds = max_wait_seconds
        self.transport = transport

    def parse_file(self, source: Path, output_dir: Path, language: str = "ch") -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        timeout = httpx.Timeout(120.0, connect=20.0)
        with httpx.Client(timeout=timeout, headers=headers, transport=self.transport) as client:
            with source.open("rb") as document:
                response = client.post(
                    f"{self.base_url}/tasks",
                    data={
                        "lang_list": language,
                        "backend": "pipeline",
                        "parse_method": "auto",
                        "image_analysis": "false",
                        "return_md": "true",
                        "return_middle_json": "false",
                        "return_model_output": "false",
                        "return_content_list": "true",
                        "return_images": "true",
                        "response_format_zip": "true",
                        "return_original_file": "false",
                    },
                    files={
                        "files": (
                            source.name,
                            document,
                            "application/octet-stream",
                        )
                    },
                )
            response.raise_for_status()
            task_id = response.json().get("task_id")
            if not isinstance(task_id, str) or not task_id:
                raise RuntimeError("MinerU API 没有返回 task_id")

            task_segment = quote(task_id, safe="")
            status_url = f"{self.base_url}/tasks/{task_segment}"
            result_url = f"{status_url}/result"
            deadline = time.monotonic() + self.max_wait_seconds
            while True:
                status_response = client.get(status_url)
                status_response.raise_for_status()
                payload = status_response.json()
                state = str(payload.get("status", "")).lower()
                if state == "failed":
                    raise RuntimeError(f"云端 MinerU 解析失败：{payload.get('error') or payload.get('message') or '未知错误'}")
                if state == "completed":
                    result_response = client.get(result_url)
                    if result_response.status_code == 202:
                        pass
                    else:
                        result_response.raise_for_status()
                        break
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"等待云端 MinerU 任务超时（{self.max_wait_seconds:g} 秒）")
                time.sleep(self.poll_interval)

            fd, temp_zip_name = tempfile.mkstemp(prefix="mineru-result-", suffix=".zip", dir=output_dir)
            os.close(fd)
            try:
                with open(temp_zip_name, "wb") as downloaded:
                    downloaded.write(result_response.content)
                if not zipfile_signature(temp_zip_name):
                    raise RuntimeError("MinerU 结果不是有效 ZIP 文件")
                safe_extract_zip(temp_zip_name, output_dir)
            finally:
                Path(temp_zip_name).unlink(missing_ok=True)

        result = find_artifacts(output_dir)
        if not result["markdown_path"]:
            raise RuntimeError("云端任务完成，但 ZIP 中没有找到 Markdown 文件")
        result["status"] = "success"
        return result


def zipfile_signature(path: str | Path) -> bool:
    with open(path, "rb") as archive:
        return archive.read(4).startswith(b"PK\x03\x04")
