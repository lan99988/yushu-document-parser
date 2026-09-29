# MinerU 4.0.7（本机项目引擎）

此目录替换了项目中的旧版 MinerU 3.2.3 引擎文件。

## 来源与许可

本目录中的 `mineru/` Python 引擎代码从 OpenDataLab 在 PyPI 发布的 MinerU 4.0.7 官方 wheel 解包而来；原始 wheel 保存在本目录，SHA-256：

`a08b24f733f0160eb9a836b0bb721640caef61d8d4f0ba2fd3aff28c6718111d`

上游项目：[OpenDataLab/MinerU](https://github.com/opendatalab/MinerU)；版本发布页：[PyPI MinerU 4.0.7](https://pypi.org/project/mineru/4.0.7/)。许可文本见 [LICENSE.md](LICENSE.md)。此处保留的是 4.0.7 发布包中的引擎代码和发行元数据，不是完整 Git 开发仓库。

## 一键启动

可以在本目录运行：

- `解析PDF.bat`：将 PDF 拖到该文件上，或在命令行传入 PDF 路径。
- `一键解析队列.bat`：顺序解析项目根目录 `解析队列\中文` 与 `解析队列\英文` 中的 PDF。
- `启动MinerU服务.bat`：手动启动本机 API 服务，仅监听 `127.0.0.1:8000`。

这些入口使用项目现有的隔离运行环境 `%LOCALAPPDATA%\DocumentParser\app\.venv`。已确认环境安装 MinerU 4.0.7，PyTorch CUDA 可用；模型缓存仍在 `%USERPROFILE%\.cache\modelscope`，不会复制到源码目录。

单文件解析与队列结果仍按项目根目录现有脚本的规则保存。详见项目根目录的 `本机文档解析升级说明.md`。
## 旧版目录状态

3.2.3 已从活动路径移走，但完整旧目录目前暂存于项目根目录的 `MinerU-mineru-3.2.3-released.retired`。自动安全审查拦截了递归删除命令，尚未物理清理该目录。需要恢复旧环境时可从该目录回滚；常规启动只使用 MinerU 4.0.7。

旧目录里的本地资料副本位于 `MinerU-3.2.3-local-data-backup-2026-09-27`。