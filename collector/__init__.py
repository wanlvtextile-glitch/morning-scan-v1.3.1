# 采集层包入口
# 对外只暴露 collect()，内部模块不直接对外使用。

from collector.entry import collect

__all__ = ['collect']
