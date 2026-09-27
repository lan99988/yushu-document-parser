from __future__ import annotations

import re
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath


def allocate_output_dir(output_root: str | Path, source_file: str | Path) -> Path:
    """Create a new output folder without replacing earlier results."""
    root = Path(output_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    stem = Path(source_file).stem.strip().rstrip(" .") or "document"
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", stem)
    if stem.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        stem = f"_{stem}"

    suffix = 1
    while True:
        name = stem if suffix == 1 else f"{stem}-{suffix}"
        candidate = root / name
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            suffix += 1


def safe_extract_zip(archive_path: str | Path, destination: str | Path) -> list[Path]:
    """Extract a ZIP only after validating every member against path traversal."""
    root = Path(destination).resolve()
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        entries: list[tuple[zipfile.ZipInfo, Path]] = []
        for member in archive.infolist():
            raw_name = member.filename.replace("\\", "/")
            relative = PurePosixPath(raw_name)
            if relative.is_absolute() or not relative.parts or any(part in {"..", ""} for part in relative.parts):
                raise ValueError(f"ZIP 中包含不安全路径：{member.filename}")
            if relative.parts[0].endswith(":"):
                raise ValueError(f"ZIP 中包含绝对路径：{member.filename}")
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError(f"ZIP 中不允许符号链接：{member.filename}")
            target = (root / Path(*relative.parts)).resolve()
            if not target.is_relative_to(root):
                raise ValueError(f"ZIP 中包含不安全路径：{member.filename}")
            entries.append((member, target))

        written: list[Path] = []
        for member, target in entries:
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            written.append(target)
        return written


def find_artifacts(output_dir: str | Path) -> dict[str, object]:
    root = Path(output_dir)
    markdown_files = sorted(path for path in root.rglob("*.md") if path.is_file())
    structured_content_files = sorted(path for path in root.rglob("structured_content.json") if path.is_file())
    middle_json_files = sorted(path for path in root.rglob("middle_json.json") if path.is_file())
    images = sorted(
        path for path in root.rglob("*")
        if path.is_file() and path.parent.name.lower() == "images"
    )
    markdown_path = markdown_files[0] if markdown_files else None
    preview = ""
    if markdown_path:
        preview = markdown_path.read_text(encoding="utf-8", errors="replace")[:600]
    return {
        "markdown_path": str(markdown_path.resolve()) if markdown_path else None,
        "structured_content_path": str(structured_content_files[0].resolve()) if structured_content_files else None,
        "middle_json_path": str(middle_json_files[0].resolve()) if middle_json_files else None,
        "image_paths": [str(path.resolve()) for path in images],
        "preview": preview,
    }
