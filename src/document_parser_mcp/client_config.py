from __future__ import annotations

import json
import argparse
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import tomlkit


def _backup(path: Path) -> None:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    shutil.copy2(path, path.with_name(f"{path.name}.backup-{stamp}"))


def register_codex_server(
    config_path: str | Path,
    server_name: str,
    command: str,
    args: list[str],
    env: dict[str, str],
) -> Path | None:
    path = Path(config_path).expanduser()
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    document = tomlkit.parse(original)
    servers = document.get("mcp_servers")
    if servers is None:
        servers = tomlkit.table()
        document["mcp_servers"] = servers
    entry = tomlkit.table()
    entry["command"] = command
    entry["args"] = args
    if env:
        environment = tomlkit.inline_table()
        for key, value in env.items():
            environment[key] = value
        entry["env"] = environment
    servers[server_name] = entry
    updated = tomlkit.dumps(document)
    if updated == original:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        _backup(path)
    path.write_text(updated, encoding="utf-8")
    return path


def register_workbuddy_server(
    config_path: str | Path,
    server_name: str,
    command: str,
    args: list[str],
    env: dict[str, str],
) -> Path | None:
    path = Path(config_path).expanduser()
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    document: dict[str, Any] = json.loads(original) if original.strip() else {}
    servers = document.setdefault("mcpServers", {})
    servers[server_name] = {"command": command, "args": args, "env": env, "disabled": False}
    updated = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if updated == original:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        _backup(path)
    path.write_text(updated, encoding="utf-8")
    return path


def configure_clients(
    codex_config: str | Path | None,
    workbuddy_config: str | Path | None,
    server_name: str,
    command: str,
    args: list[str],
    env: dict[str, str],
) -> dict[str, Path | None]:
    result: dict[str, Path | None] = {}
    if codex_config:
        result["codex"] = register_codex_server(codex_config, server_name, command, args, env)
    if workbuddy_config:
        result["workbuddy"] = register_workbuddy_server(workbuddy_config, server_name, command, args, env)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="将文档解析 MCP 合并到 Codex 和 WorkBuddy 配置")
    parser.add_argument("--codex-config")
    parser.add_argument("--workbuddy-config")
    parser.add_argument("--server-name", required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--args-json", required=True)
    parser.add_argument("--env-json", required=True)
    options = parser.parse_args()
    result = configure_clients(
        options.codex_config,
        options.workbuddy_config,
        options.server_name,
        options.command,
        json.loads(options.args_json),
        json.loads(options.env_json),
    )
    for client, updated_path in result.items():
        print(f"{client}: {updated_path or '配置已是最新'}")


if __name__ == "__main__":
    main()
