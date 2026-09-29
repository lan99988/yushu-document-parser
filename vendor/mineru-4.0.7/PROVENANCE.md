# MinerU 4.0.7 来源记录

- 上游项目： [OpenDataLab/MinerU](https://github.com/opendatalab/MinerU)
- 上游发行包： [PyPI `mineru` 4.0.7](https://pypi.org/project/mineru/4.0.7/)
- wheel 文件：`mineru-4.0.7-py3-none-any.whl`
- SHA-256：`a08b24f733f0160eb9a836b0bb721640caef61d8d4f0ba2fd3aff28c6718111d`
- `mineru/` 和 `mineru-4.0.7.dist-info/` 是从上述官方 wheel 解出的发布内容；原始 wheel 一并保留。
- 这不是 MinerU 完整的上游 Git 仓库，也不是本项目自行实现或修改的 MinerU fork。
- 上游许可文本保存在本目录 `LICENSE.md` 和 `.dist-info/licenses/`；本项目的 MIT 许可不覆盖这些上游文件。
- 安装器和云端容器从此目录的原始 wheel 安装 MinerU；wheel 的 Python 依赖由包管理器获取。模型权重、依赖缓存、虚拟环境和解析产物不随仓库发布。
