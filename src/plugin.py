"""插件基类与插件加载模块。

依据 docs/plugin_design.md 实现：

- 第 4 节《插件入口》：插件主文件必须导出固定名称 ``PLUGIN`` 的插件入口对象，
  且必须是插件主类本身（类对象，而非实例或函数）。
- 第 5 节《插件主类》：插件主类必须继承框架提供的插件基类，由框架实例化，
  并提供插件元数据与生命周期函数。
- 第 6 节《插件生命周期》：第一版只暴露 ``on_load`` / ``on_unload`` 两个阶段，
  载入阶段抛出的异常作为插件载入失败的评判标准。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

import log

__all__ = ["PluginBase", "load", "PLUGIN_ENTRY_NAME"]

#: 插件主文件中插件入口对象的固定名称（设计文档第 4 节）
PLUGIN_ENTRY_NAME = "PLUGIN"


class PluginBase(BaseModel):
    """插件主类基类（设计文档第 5、6 节）。

    插件主类是插件的唯一生命周期载体，必须由框架实例化。

    继承 :class:`pydantic.BaseModel`，插件元数据以 pydantic 字段形式
    声明在子类上，实例化时由 pydantic 自动完成类型与约束校验：

    - ``plugin_id``: 插件标识，必须与插件目录名一致；
    - ``name``: 插件名称；
    - ``version``: 插件版本，采用语义化版本；
    - ``framework_version``: 框架兼容版本范围，不得为空；
    - ``description``: 插件描述；
    - ``author``: 作者或维护者。

    子类还必须实现 :meth:`on_load` 与 :meth:`on_unload` 生命周期函数。
    """

    # validate_default=True: 子类以默认值形式声明的元数据字段也会经过校验
    # arbitrary_types_allowed=True: 允许 context 等任意类型字段
    model_config = ConfigDict(validate_default=True, arbitrary_types_allowed=True)

    # ---- 插件元数据字段（子类必须覆盖默认值为空的必填字段） ----
    plugin_id: str = Field(default="", min_length=1)
    name: str = Field(default="", min_length=1)
    version: str = Field(default="", min_length=1)
    framework_version: str = Field(default="", min_length=1)
    description: str = ""
    author: str = ""

    # ---- 框架注入的运行时成员 ----
    _context: Any = PrivateAttr(default=None)
    _logger: Optional[log.LoggerBase] = PrivateAttr(default=None)
    _loaded: bool = PrivateAttr(default=False)

    def model_post_init(self, context: Any, /) -> None:
        """pydantic 校验完成后的初始化钩子，由框架实例化流程触发。"""
        if type(self) is PluginBase:
            raise TypeError("PluginBase 为抽象基类，不得直接实例化")
        self._logger = log.LoggerBase(category="plugin", ident=self.plugin_id)

    @property
    def context(self) -> Any:
        """框架注入的插件上下文。"""
        return self._context

    @property
    def logger(self) -> log.LoggerBase:
        """框架提供的日志接口（设计文档第 30 节）。"""
        assert self._logger is not None
        return self._logger

    @property
    def loaded(self) -> bool:
        """插件是否已完成载入。"""
        return self._loaded

    def on_load(self) -> None:
        """载入阶段生命周期函数，由框架调用。

        插件可在此初始化内部状态、读取设置、注册能力、
        提交后台任务、建立外部连接。抛出的任何异常都会被框架捕获，
        并作为插件载入失败的评判标准。
        """
        raise NotImplementedError

    def on_unload(self) -> None:
        """卸载阶段生命周期函数，由框架调用。

        插件必须在此停止长期运行的资源、关闭外部连接、
        释放文件句柄/线程/子进程，并保证不再持有框架资源。
        """
        raise NotImplementedError


def load(fn: Path) -> PluginBase | None:
    """从插件主文件路径加载插件（设计文档第 3、4 节）。

    加载流程：

    1. 以独立模块名导入插件主文件；
    2. 读取固定名称 ``PLUGIN`` 的插件入口对象；
    3. 校验入口对象必须是 :class:`PluginBase` 的子类（类对象）；
    4. 由框架实例化并返回插件实例。

    任何一步失败均返回 ``None``，不抛出异常。

    :param fn: 插件主文件路径（如 ``plugins/demo/main.py``）。
    :returns: 插件主类实例，失败时返回 ``None``。
    """
    fn = Path(fn)
    logger = log.plugin_logger

    if not fn.is_file():
        logger.error(f"插件主文件不存在: {fn}")
        return None

    # 插件目录名作为插件唯一标识（设计文档第 3 节）
    plugin_id = fn.resolve().parent.name
    package_name = f"_plugin_{plugin_id}"
    module_name = f"{package_name}.{fn.stem}"

    # 由框架为插件准备导入环境：保证框架源码目录在 sys.path 中，
    # 插件可直接 `from plugin import PluginBase`，无需自行处理路径
    framework_dir = str(Path(__file__).resolve().parent)
    if framework_dir not in sys.path:
        sys.path.insert(0, framework_dir)

    try:
        # 为插件目录创建包模块，使插件主文件可以使用相对导入
        # （如 `from .demo_class import DemoPlugin`）
        package = ModuleType(package_name)
        package.__path__ = [str(fn.resolve().parent)]  # type: ignore[attr-defined]
        sys.modules[package_name] = package

        spec = importlib.util.spec_from_file_location(module_name, fn)
        if spec is None or spec.loader is None:
            logger.error(f"无法为插件创建模块 spec: {fn}")
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(module_name, None)
            sys.modules.pop(package_name, None)
            raise
    except Exception as exc:
        logger.error(f"插件主文件导入失败 [{plugin_id}]: {exc}")
        return None

    # 框架只读取插件入口对象，不调用插件入口函数（设计文档第 4 节）
    entry = getattr(module, PLUGIN_ENTRY_NAME, None)
    if entry is None:
        logger.error(f"插件未导出入口对象 {PLUGIN_ENTRY_NAME}: {fn}")
        return None
    if not isinstance(entry, type):
        logger.error(
            f"插件入口对象必须是类对象，实际为 {type(entry).__name__}: {fn}"
        )
        return None
    if not issubclass(entry, PluginBase):
        logger.error(f"插件主类必须继承 PluginBase: {fn}")
        return None

    try:
        instance = entry()
    except Exception as exc:
        logger.error(f"插件主类实例化失败 [{plugin_id}]: {exc}")
        return None

    # 插件标识必须与插件目录名一致（设计文档第 5 节）
    if instance.plugin_id != plugin_id:
        logger.error(f"插件标识 {instance.plugin_id!r} 与目录名 {plugin_id!r} 不一致")
        return None

    logger.info(f"插件加载成功: {instance.name} v{instance.version}")
    return instance
