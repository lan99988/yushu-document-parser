from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .artifacts import find_artifacts


class LocalMinerUBackend:
    """Run the installed MinerU 3.2.3 CLI in the adapter's Python environment."""

    def __init__(self, runner=None):
        self.runner = runner or subprocess.run

    def parse_file(self, source: Path, output_dir: Path, language: str = "ch") -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            "-m",
            "mineru.cli.client",
            "-p",
            str(source.resolve()),
            "-o",
            str(output_dir.resolve()),
            "-b",
            "pipeline",
            "-m",
            "auto",
            "-l",
            language,
        ]
        completed = self.runner(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "MinerU 未提供错误详情").strip()
            raise RuntimeError(f"本机 MinerU 解析失败：{detail[-2000:]}")
        result = find_artifacts(output_dir)
        if not result["markdown_path"]:
            raise RuntimeError("MinerU 已退出，但输出目录中没有找到 Markdown 文件")
        return result
