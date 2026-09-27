from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .artifacts import allocate_output_dir, find_artifacts


SUPPORTED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff",
    ".docx", ".pptx", ".xlsx",
}


class ParserService:
    def __init__(
        self,
        output_root: str | Path,
        backends: Mapping[str, object],
        default_backend: str = "local",
    ):
        self.output_root = Path(output_root).expanduser()
        self.backends = dict(backends)
        self.default_backend = default_backend

    def parse_one(self, file_path: str, language: str = "ch", backend: str | None = None) -> dict:
        source = Path(file_path).expanduser().resolve()
        selected_backend = backend or self.default_backend
        if not source.is_file():
            return self._error(source, selected_backend, f"文件不存在：{source}")
        if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return self._error(source, selected_backend, f"不支持的文件类型：{source.suffix or '无扩展名'}")
        implementation = self.backends.get(selected_backend)
        if implementation is None:
            return self._error(source, selected_backend, f"后端“{selected_backend}”未配置；未自动切换到其他后端")

        output_dir = allocate_output_dir(self.output_root, source)
        try:
            backend_result = implementation.parse_file(source, output_dir, language=language)
            artifacts = find_artifacts(output_dir)
            if isinstance(backend_result, dict):
                artifacts.update({key: value for key, value in backend_result.items() if key in {"markdown_path", "content_list_path", "image_paths", "preview"} and value is not None})
            if not artifacts["markdown_path"]:
                raise RuntimeError("解析没有生成 Markdown 文件")
            return {
                "status": "success",
                "input_path": str(source),
                "backend": selected_backend,
                "output_dir": str(output_dir.resolve()),
                **artifacts,
            }
        except Exception as exc:
            return {
                **self._error(source, selected_backend, str(exc)),
                "output_dir": str(output_dir.resolve()),
            }

    def parse_many(self, file_paths: list[str], language: str = "ch", backend: str | None = None) -> list[dict]:
        return [self.parse_one(path, language=language, backend=backend) for path in file_paths]

    def read_text(
        self,
        markdown_path: str,
        *,
        start_line: int = 1,
        max_lines: int = 200,
        full: bool = False,
    ) -> dict:
        path = Path(markdown_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Markdown 文件不存在：{path}")
        if path.suffix.lower() != ".md":
            raise ValueError("读取工具只接受 Markdown 文件路径")
        if start_line < 1:
            raise ValueError("start_line 必须大于等于 1")
        if max_lines < 1 and not full:
            raise ValueError("max_lines 必须大于等于 1")
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        start_index = min(start_line - 1, len(lines))
        end_index = len(lines) if full else min(len(lines), start_index + max_lines)
        return {
            "markdown_path": str(path),
            "start_line": start_index + 1,
            "end_line": end_index,
            "next_line": end_index + 1 if end_index < len(lines) else None,
            "total_lines": len(lines),
            "has_more": end_index < len(lines),
            "text": "\n".join(lines[start_index:end_index]),
        }

    @staticmethod
    def _error(source: Path, backend: str, message: str) -> dict:
        return {"status": "error", "input_path": str(source), "backend": backend, "error": message}
