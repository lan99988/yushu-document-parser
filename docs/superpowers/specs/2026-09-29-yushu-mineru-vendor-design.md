# Yushu Document Parser 与 MinerU 4.0.7 整合设计

## 目标

在现有 `yushu-document-parser` 仓库中整合 MCP 适配器和 MinerU 4.0.7 核心发布包，并统一使用 `main` 分支发布。MCP 在客户端中的名称统一为 `yushu-document-parser`。

## 当前状态

- MCP 代码位于 `src/document_parser_mcp/`，客户端注册键和 FastMCP 服务名当前为 `document-parser`。
- Windows 安装器和云端 Dockerfile 当前从包源安装 MinerU 4.0.7。
- 本地 `MinerU-mineru-4.0.7-released` 目录源自 OpenDataLab 发布到 PyPI 的 `mineru-4.0.7-py3-none-any.whl`，含可读的 `mineru/` 源码、发行元数据和原始 wheel；它不是完整上游 Git 仓库。
- 原始 wheel 的 SHA-256 为 `a08b24f733f0160eb9a836b0bb721640caef61d8d4f0ba2fd3aff28c6718111d`。

## 设计

### 仓库布局与上游内容

在仓库 `vendor/mineru-4.0.7/` 下保存 MinerU 官方 wheel 解出的可读引擎源码和必要发行元数据，并保留原始官方 wheel、上游 README、许可文本及来源说明。记录版本、下载来源和 SHA-256，便于复核发行包。不要复制 `__pycache__`、本机验证输出、模型、虚拟环境、用户文件或解析产物。

仓库自己的 `LICENSE` 继续适用于 MCP 适配器代码。MinerU 按其上游许可单独分发：保留随版本提供的许可和归属信息，并在 README 清楚说明 Apache 2.0 基础许可及其附加条款，不暗示 MinerU 代码也受本仓库 MIT 许可。

### 安装与运行

- Windows 本机安装器从安装目录中携带的官方 MinerU wheel 安装 4.0.7，依赖仍由 pip/uv 按 wheel 元数据解析；GPU 与 CPU 的 PyTorch 选择流程保持现状。
- Docker 构建上下文调整为仓库根目录，Dockerfile 从 `vendor/mineru-4.0.7/` 安装同一 wheel；CPU/GPU 配置和模型缓存策略保持现状。
- MCP 工具入口、产物格式以及本机/远程后端行为不变。

### MCP 命名和升级迁移

- FastMCP 服务身份与 Codex `mcp_servers`、WorkBuddy `mcpServers` 配置键统一改为 `yushu-document-parser`。
- `parse_document`、`parse_documents`、`read_parsed_text` 工具名，Python 包 `document_parser_mcp` 和现有 Skill 名称保持稳定。
- 安装器更新客户端配置前照常备份。若存在旧 `document-parser` 配置，只有在其启动参数明确指向 `document_parser_mcp.server` 时才移除旧键；保留不相关的同名或自定义服务配置。

### 文档和验收

README 更新上游来源、仓库目录、安装流程、MCP 名称和许可边界，并说明项目包含的是 MinerU 4.0.7 PyPI 发布包而非完整上游 Git 仓库。安装器、云端模板和配置迁移测试覆盖新路径；现有功能测试继续验证本机与远程解析行为。最终在现有 `main` 上提交并推送整合结果。

## 不在范围内

- 不纳入 MinerU 模型权重、缓存、Python 运行环境、依赖 wheel 集合或解析结果。
- 不更改 MCP 工具 schema、Python 导入名、Skill 名称、本机/云端 API 语义或 `book-to-skill` 工作流。
- 不声称本仓库是 MinerU 官方仓库或完整 fork。
