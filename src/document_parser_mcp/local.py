from __future__ import annotations

from pathlib import Path
from typing import Callable

from .artifacts import find_artifacts


class LocalMinerUBackend:
    """Parse a document with the MinerU 4 Python SDK installed in this environment."""

    def __init__(self, *, parser: Callable | None = None, writer_factory: Callable | None = None):
        self.parser = parser
        self.writer_factory = writer_factory

    def _load_sdk(self) -> tuple[Callable, Callable]:
        parser = self.parser
        writer_factory = self.writer_factory
        if parser is None:
            try:
                from mineru.parser import parse
            except ImportError as exc:
                raise RuntimeError("未安装本机 MinerU 4.0.7；请重装本机模式或选择 remote 后端") from exc
            parser = parse
        if writer_factory is None:
            try:
                from mineru.parser.writer import FileBasedDataWriter
            except ImportError as exc:
                raise RuntimeError("MinerU 4.0.7 文件输出组件不可用，请重新安装 MinerU") from exc
            writer_factory = FileBasedDataWriter
        return parser, writer_factory

    def parse_file(self, source: Path, output_dir: Path, tier: str = "standard") -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        parser, writer_factory = self._load_sdk()
        try:
            result = parser(str(source.resolve()), tier=tier)
            writer = writer_factory(str(output_dir.resolve()))
            result.save(writer)
        except Exception as exc:
            raise RuntimeError(f"本机 MinerU 4.0.7 解析失败：{exc}") from exc

        artifacts = find_artifacts(output_dir)
        if not artifacts["markdown_path"]:
            raise RuntimeError("MinerU 4.0.7 已完成，但没有生成 Markdown 文件")
        if not artifacts["structured_content_path"]:
            raise RuntimeError("MinerU 4.0.7 已完成，但没有生成 structured_content.json")
        return artifacts
