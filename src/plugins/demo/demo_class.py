"""演示插件主类。

依据 docs/plugin_design.md 第 5、6 节实现：

1. 插件主类必须继承框架提供的插件基类 :class:`PluginBase`；
2. 插件元数据直接以类属性形式声明；
3. 插件主类必须提供 ``on_load`` / ``on_unload`` 生命周期函数。
"""

# 框架在加载插件时已保证框架源码目录位于 sys.path 中，
# 插件可直接导入框架模块，无需自行处理路径
from plugin import PluginBase


class DemoPlugin(PluginBase):
    """演示插件，展示插件主类的最小实现。"""

    plugin_id: str = "demo"  # 必须与插件目录名一致
    name: str = "演示插件"
    version: str = "0.1.0"
    framework_version: str = ">=0.1.0"
    description: str = "用于演示插件系统接入方式的最小插件"
    author: str = "all-in-one-downloader"

    def on_load(self) -> None:
        """载入阶段：初始化内部状态并注册能力（此处仅记录日志）。"""
        self.logger.info(f"插件 {self.name} 载入完成")

    def on_unload(self) -> None:
        """卸载阶段：释放插件持有的资源（此处仅记录日志）。"""
        self.logger.info(f"插件 {self.name} 已卸载")
