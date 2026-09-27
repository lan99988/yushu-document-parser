from __future__ import annotations

import hashlib
import httpx
import mimetypes
import os
import tempfile
import time
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit

from .artifacts import find_artifacts, safe_extract_zip


class RemoteMinerUBackend:
    """Use MinerU 4's V1 upload/job API and save its ZIP artifacts locally."""

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        poll_interval: float = 3.0,
        max_wait_seconds: float = 1800.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.poll_interval = max(0.0, poll_interval)
        self.max_wait_seconds = max_wait_seconds
        self.transport = transport

    def parse_file(self, source: Path, output_dir: Path, tier: str = "standard") -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        timeout = httpx.Timeout(120.0, connect=20.0)
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        with httpx.Client(timeout=timeout, headers=headers, transport=self.transport) as client:
            file_id = self._upload(client, source, timeout)
            job = self._create_job(client, file_id, tier)
            job = self._wait_for_job(client, job, timeout)
            file_entry = self._successful_file(job, source.name)
            archive_id = self._output_file_id(file_entry)

            fd, temp_zip_name = tempfile.mkstemp(prefix="mineru-v4-result-", suffix=".zip", dir=output_dir)
            os.close(fd)
            try:
                self._download_file(archive_id, Path(temp_zip_name), timeout)
                if not zipfile_signature(temp_zip_name):
                    raise RuntimeError("MinerU V1 返回的 ZIP 结果无效")
                safe_extract_zip(temp_zip_name, output_dir)
            finally:
                Path(temp_zip_name).unlink(missing_ok=True)

        artifacts = find_artifacts(output_dir)
        if not artifacts["markdown_path"]:
            raise RuntimeError("云端任务完成，但 ZIP 中没有找到 Markdown 文件")
        if not artifacts["structured_content_path"]:
            raise RuntimeError("云端任务完成，但 ZIP 中没有找到 structured_content.json")
        return {"status": "success", **artifacts}

    def _api_url(self, path: str) -> str:
        return f"{self.base_url}/v1/{path.lstrip('/')}"

    def _upload(self, client: httpx.Client, source: Path, timeout: httpx.Timeout) -> str:
        digest = hashlib.sha256()
        with source.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        size = source.stat().st_size
        mime_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        create_response = client.post(
            self._api_url("uploads"),
            json={
                "filename": source.name,
                "bytes": size,
                "mime_type": mime_type,
                "purpose": "parse",
                "sha256sum": digest.hexdigest(),
            },
        )
        create_response.raise_for_status()
        upload = create_response.json()
        status = upload.get("status")
        if status == "completed":
            file_id = (upload.get("file") or {}).get("id")
            if isinstance(file_id, str) and file_id:
                return file_id
            raise RuntimeError("MinerU V1 去重上传响应缺少 file.id")
        if status != "pending":
            raise RuntimeError(f"MinerU V1 上传创建返回未知状态：{status!r}")

        upload_id = _required_string(upload, "id", "创建上传")
        upload_url = _required_string(upload, "upload_url", "创建上传")
        method = str(upload.get("upload_method") or "PUT").upper()
        if method != "PUT":
            raise RuntimeError(f"MinerU V1 返回了不支持的上传方法：{method}")
        target_url = urljoin(f"{self.base_url}/", upload_url)
        request_headers = _upload_headers(upload.get("upload_headers"))
        if _same_origin(self.base_url, target_url) and self.token and not _has_header(request_headers, "Authorization"):
            request_headers["Authorization"] = f"Bearer {self.token}"
        request_headers.setdefault("Content-Length", str(size))

        # A pre-signed storage URL may be on another origin. Use a separate client
        # so the API bearer token is never inherited by that upload request.
        with httpx.Client(timeout=timeout, headers=request_headers, transport=self.transport) as upload_client:
            with source.open("rb") as document:
                uploaded = upload_client.put(target_url, content=document)
            uploaded.raise_for_status()

        complete_response = client.post(self._api_url(f"uploads/{quote(upload_id, safe='')}/complete"))
        complete_response.raise_for_status()
        completed = complete_response.json()
        if completed.get("status") != "completed":
            raise RuntimeError(f"MinerU V1 上传完成阶段返回未知状态：{completed.get('status')!r}")
        file_id = (completed.get("file") or {}).get("id")
        if not isinstance(file_id, str) or not file_id:
            raise RuntimeError("MinerU V1 上传完成响应缺少 file.id")
        return file_id

    def _create_job(self, client: httpx.Client, file_id: str, tier: str) -> dict:
        response = client.post(
            self._api_url("parse/jobs"),
            json={
                "files": [{"source": {"type": "file_id", "file_id": file_id}}],
                "tier": tier,
                "output_formats": ["zip"],
            },
        )
        response.raise_for_status()
        job = response.json()
        _required_string(job, "job_id", "创建解析任务")
        self._validate_job_status(job)
        return job

    def _wait_for_job(self, client: httpx.Client, job: dict, timeout: httpx.Timeout) -> dict:
        state = str(job.get("status", "")).lower()
        deadline = time.monotonic() + self.max_wait_seconds
        while state not in {"completed", "partial", "failed", "canceled"}:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"等待 MinerU V1 任务超时（{self.max_wait_seconds:g} 秒）；远程任务不会自动取消")
            time.sleep(self.poll_interval)
            job_id = quote(_required_string(job, "job_id", "轮询解析任务"), safe="")
            response = client.get(self._api_url(f"parse/jobs/{job_id}"), timeout=timeout)
            response.raise_for_status()
            job = response.json()
            self._validate_job_status(job)
            state = str(job.get("status", "")).lower()
        if state == "failed":
            raise RuntimeError(_job_error("云端 MinerU 解析失败", job))
        if state == "canceled":
            raise RuntimeError("云端 MinerU 解析任务已取消")
        return job

    @staticmethod
    def _validate_job_status(job: dict) -> None:
        state = str(job.get("status", "")).lower()
        if state not in {"queued", "running", "completed", "partial", "failed", "canceled"}:
            raise RuntimeError(f"MinerU V1 返回未知任务状态：{state!r}")

    @staticmethod
    def _successful_file(job: dict, filename: str) -> dict:
        files = job.get("files")
        if not isinstance(files, list):
            raise RuntimeError("MinerU V1 已结束，但响应中没有 files 列表")
        matching = [entry for entry in files if isinstance(entry, dict) and entry.get("name") == filename]
        if not matching and len(files) == 1 and isinstance(files[0], dict):
            matching = files
        if not matching:
            raise RuntimeError(f"MinerU V1 结果中没有输入文件 {filename!r}")
        entry = matching[0]
        if entry.get("status") != "completed":
            raise RuntimeError(_file_error(f"云端 MinerU 未能解析 {filename}", entry))
        return entry

    @staticmethod
    def _output_file_id(file_entry: dict) -> str:
        output_files = file_entry.get("output_files")
        archive = output_files.get("zip") if isinstance(output_files, dict) else None
        file_id = archive.get("file_id") if isinstance(archive, dict) else None
        if not isinstance(file_id, str) or not file_id:
            raise RuntimeError("MinerU V1 ZIP 输出缺少 file_id")
        return file_id

    def _download_file(self, file_id: str, destination: Path, timeout: httpx.Timeout) -> None:
        current_url = self._api_url(f"files/{quote(file_id, safe='')}/content")
        for _ in range(6):
            headers = {"Authorization": f"Bearer {self.token}"} if self.token and _same_origin(self.base_url, current_url) else {}
            with httpx.Client(timeout=timeout, headers=headers, transport=self.transport, follow_redirects=False) as client:
                with client.stream("GET", current_url) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise RuntimeError("MinerU V1 文件下载重定向缺少 Location")
                        current_url = urljoin(current_url, location)
                        continue
                    response.raise_for_status()
                    with destination.open("wb") as downloaded:
                        for chunk in response.iter_bytes():
                            downloaded.write(chunk)
                    return
        raise RuntimeError("MinerU V1 文件下载重定向次数过多")


def _required_string(payload: dict, key: str, stage: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"MinerU V1 {stage}响应缺少有效的 {key}")
    return value


def _upload_headers(value: object) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in value.items()):
        raise RuntimeError("MinerU V1 upload_headers 必须是字符串键值映射")
    if any("\r" in key or "\n" in key or "\r" in item or "\n" in item for key, item in value.items()):
        raise RuntimeError("MinerU V1 upload_headers 包含换行字符")
    return dict(value)


def _has_header(headers: dict[str, str], name: str) -> bool:
    return any(key.lower() == name.lower() for key in headers)


def _same_origin(first: str, second: str) -> bool:
    try:
        left = urlsplit(first)
        right = urlsplit(second)
        if left.scheme.lower() not in {"http", "https"} or right.scheme.lower() not in {"http", "https"}:
            return False
        left_origin = (left.scheme.lower(), (left.hostname or "").lower(), left.port or (443 if left.scheme.lower() == "https" else 80))
        right_origin = (right.scheme.lower(), (right.hostname or "").lower(), right.port or (443 if right.scheme.lower() == "https" else 80))
        return bool(left_origin[1]) and left_origin == right_origin
    except ValueError:
        return False


def _job_error(prefix: str, job: dict) -> str:
    error = job.get("error") or job.get("message")
    return f"{prefix}：{error or '未知错误'}"


def _file_error(prefix: str, file_entry: dict) -> str:
    error = file_entry.get("error")
    if isinstance(error, dict):
        detail = f"{error.get('code') or 'error'}: {error.get('message') or '未知错误'}"
    else:
        detail = str(error or "未知错误")
    return f"{prefix}：{detail}"


def zipfile_signature(path: str | Path) -> bool:
    with open(path, "rb") as archive:
        return archive.read(4).startswith(b"PK\x03\x04")
