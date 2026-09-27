from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import tomlkit

from document_parser_mcp.client_config import configure_clients, register_codex_server, register_workbuddy_server


class ClientConfigTests(unittest.TestCase):
    def test_shared_registration_updates_both_clients(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = configure_clients(
                root / "config.toml",
                root / "mcp.json",
                "document-parser",
                "python.exe",
                ["-m", "document_parser_mcp.server"],
                {"DOCUMENT_PARSER_BACKEND": "remote"},
            )

            self.assertEqual(set(result), {"codex", "workbuddy"})
            self.assertTrue((root / "config.toml").is_file())
            self.assertTrue((root / "mcp.json").is_file())

    def test_codex_merge_preserves_existing_servers_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "config.toml"
            config.write_text('[mcp_servers.existing]\ncommand = "keep"\n', encoding="utf-8")

            register_codex_server(config, "document-parser", "python.exe", ["-m", "document_parser_mcp.server"], {})
            content = config.read_text(encoding="utf-8")
            backups_before_second_run = list(config.parent.glob("config.toml.backup-*"))
            register_codex_server(config, "document-parser", "python.exe", ["-m", "document_parser_mcp.server"], {})

            parsed = tomlkit.parse(content)
            self.assertEqual(parsed["mcp_servers"]["existing"]["command"], "keep")
            self.assertEqual(parsed["mcp_servers"]["document-parser"]["command"], "python.exe")
            self.assertEqual(len(list(config.parent.glob("config.toml.backup-*"))), len(backups_before_second_run))
            self.assertTrue(backups_before_second_run)

    def test_workbuddy_merge_preserves_existing_entries_and_creates_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "mcp.json"
            config.write_text(json.dumps({"mcpServers": {"existing": {"command": "keep"}}}), encoding="utf-8")

            register_workbuddy_server(config, "document-parser", "python.exe", ["-m", "document_parser_mcp.server"], {})

            parsed = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(parsed["mcpServers"]["existing"]["command"], "keep")
            self.assertEqual(parsed["mcpServers"]["document-parser"]["command"], "python.exe")
            self.assertTrue(list(config.parent.glob("mcp.json.backup-*")))


if __name__ == "__main__":
    unittest.main()
