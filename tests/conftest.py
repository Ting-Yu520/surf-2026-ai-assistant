"""pytest 配置：注册自定义 marker，设置 import 路径"""
import sys
from pathlib import Path

# 遵循项目导入约定：将 src/ 加入 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: 标记需要外部资源（视频/API）的慢速测试")
