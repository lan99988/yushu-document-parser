from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from document_parser_mcp.local import LocalMinerUBackend
from document_parser_mcp.remote import RemoteMinerUBackend
from document_parser_mcp.server import build_service, create_server


class ServerTests(unittest.TestCase):
    def test_local_is_default_and_remote_is_only_registered_when_configured(self):
        with tempfile.TemporaryDirectory() as temporary:
            service = build_service({"DOCUMENT_PARSER_OUTPUT_DIR": temporary})
            self.assertEqual(service.default_backend, "local")
            self.assertIsInstance(service.backends["local"], LocalMinerUBackend)
            self.assertNotIn("remote", service.backends)

    def test_remote_backend_can_be_selected_without_removing_local_backend(self):
        service = build_service(
            {
                "DOCUMENT_PARSER_OUTPUT_DIR": "D:/解析 输出",
                "DOCUMENT_PARSER_BACKEND": "remote",
                "DOCUMENT_PARSER_REMOTE_URL": "http://mineru.tailnet:8000",
                "DOCUMENT_PARSER_REMOTE_TOKEN": "secret",
            }
        )
        self.assertEqual(service.default_backend, "remote")
        self.assertIsInstance(service.backends["local"], LocalMinerUBackend)
        self.assertIsInstance(service.backends["remote"], RemoteMinerUBackend)
        self.assertEqual(service.backends["remote"].token, "secret")

    def test_server_exposes_the_three_skill_tool_names(self):
        server = create_server(build_service({}))
        tools = asyncio.run(server.list_tools())

        self.assertEqual(
            {tool.name for tool in tools},
            {"parse_document", "parse_documents", "read_parsed_text"},
        )
        parse_tool = next(tool for tool in tools if tool.name == "parse_document")
        self.assertEqual(parse_tool.inputSchema["properties"]["tier"]["default"], "auto")
        self.assertEqual(
            parse_tool.inputSchema["properties"]["tier"]["enum"],
            ["auto", "flash", "basic", "standard", "advanced"],
        )

    def test_stdio_protocol_client_can_initialize_and_discover_tools(self):
        async def discover() -> set[str]:
            env = os.environ.copy()
            with tempfile.TemporaryDirectory() as temporary:
                env["DOCUMENT_PARSER_OUTPUT_DIR"] = temporary
                parameters = StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "document_parser_mcp.server"],
                    env=env,
                )
                async with stdio_client(parameters) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        response = await session.list_tools()
                        return {tool.name for tool in response.tools}

        self.assertEqual(
            asyncio.run(discover()),
            {"parse_document", "parse_documents", "read_parsed_text"},
        )


if __name__ == "__main__":
    unittest.main()
