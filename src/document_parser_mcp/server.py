from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Mapping

from mcp.server.fastmcp import FastMCP

from .local import LocalMinerUBackend
from .remote import RemoteMinerUBackend
from .service import ParserService


def default_output_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "DocumentParser" / "output"
    return Path.home() / ".local" / "share" / "document-parser" / "output"


def build_service(env: Mapping[str, str] | None = None) -> ParserService:
    values = os.environ if env is None else env
    backend_name = values.get("DOCUMENT_PARSER_BACKEND", "local").strip().lower()
    if backend_name not in {"local", "remote"}:
        raise ValueError("DOCUMENT_PARSER_BACKEND 只能设置为 local 或 remote")

    backends: dict[str, object] = {"local": LocalMinerUBackend()}
    remote_url = values.get("DOCUMENT_PARSER_REMOTE_URL", "").strip()
    if remote_url:
        backends["remote"] = RemoteMinerUBackend(
            remote_url,
            token=values.get("DOCUMENT_PARSER_REMOTE_TOKEN") or None,
            poll_interval=float(values.get("DOCUMENT_PARSER_POLL_INTERVAL", "3")),
            max_wait_seconds=float(values.get("DOCUMENT_PARSER_MAX_WAIT_SECONDS", "1800")),
        )
    if backend_name == "remote" and "remote" not in backends:
        raise ValueError("已选择 remote 后端，但未配置 DOCUMENT_PARSER_REMOTE_URL")

    output_dir = Path(values.get("DOCUMENT_PARSER_OUTPUT_DIR", str(default_output_dir()))).expanduser()
    return ParserService(output_dir, backends, default_backend=backend_name)


def create_server(service: ParserService | None = None) -> FastMCP:
    parser = service or build_service()
    server = FastMCP("document-parser")

    @server.tool()
    def parse_document(
        file_path: str,
        tier: Literal["auto", "flash", "basic", "standard", "advanced"] = "auto",
        backend: Literal["local", "remote"] | None = None,
    ) -> dict:
        """解析 MinerU 4 支持的单个文档，并返回产物路径和短预览。"""
        return parser.parse_one(file_path, tier=tier, backend=backend)

    @server.tool()
    def parse_documents(
        file_paths: list[str],
        tier: Literal["auto", "flash", "basic", "standard", "advanced"] = "auto",
        backend: Literal["local", "remote"] | None = None,
    ) -> list[dict]:
        """按给定顺序逐个解析多个文件；单个文件失败不会中止后续处理。"""
        return parser.parse_many(file_paths, tier=tier, backend=backend)

    @server.tool()
    def read_parsed_text(
        markdown_path: str,
        start_line: int = 1,
        max_lines: int = 200,
        full: bool = False,
    ) -> dict:
        """分段读取解析生成的 Markdown；仅在明确需要时使用 full=true 返回全文。"""
        return parser.read_text(
            markdown_path,
            start_line=start_line,
            max_lines=max_lines,
            full=full,
        )

    return server


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
