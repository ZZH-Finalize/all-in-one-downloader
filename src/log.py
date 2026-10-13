"""日志基类模块。

依据 docs/plugin_design.md 第 30 节《日志与可观测性》规范实现：

1. 插件必须使用框架提供的日志接口。
2. 日志必须包含插件标识。
3. 能力执行日志应包含能力标识和任务标识。
4. 日志不得输出敏感设置。
5. 日志不得输出完整凭据、令牌或 Cookie 内容。
6. 异常日志应保留必要上下文，但不得泄露敏感信息。

输出格式示例::

    [INFO][framework][task]: task cancelled
"""

from __future__ import annotations

import logging
import sys
from typing import IO, Optional, Union

__all__ = ["LoggerBase", "LOG_FORMAT"]

#: 统一日志格式: [级别][类别][标识]: 消息
LOG_FORMAT = "[%(levelname)s][%(category)s][%(ident)s]: %(message)s"


class _ContextFilter(logging.Filter):
    """向日志记录注入类别与标识上下文字段。"""

    def __init__(self, category: str, ident: str) -> None:
        super().__init__()
        self._category = category
        self._ident = ident

    def filter(self, record: logging.LogRecord) -> bool:
        record.category = self._category
        record.ident = self._ident
        return True


class LoggerBase(logging.Logger):
    """框架日志基类，派生自 :class:`logging.Logger`。

    实例化时接收两个参数:

    - ``category``: 日志类别，例如 ``framework``、插件标识、能力标识。
    - ``ident``: 日志标识，例如任务标识、插件实例标识。

    实例可像标准 logging 一样使用 ``debug``/``info``/``warning``/
    ``error``/``critical``/``exception`` 等方法输出日志。

    默认仅向 ``stdout`` 输出，可通过 :meth:`add_output` 添加新的输出源
    （文件路径、文件对象或任意 :class:`logging.Handler`）。
    """

    def __init__(
        self,
        category: str,
        ident: str,
        level: Union[int, str] = logging.DEBUG,
    ) -> None:
        if not category:
            raise ValueError("category 不能为空")
        if not ident:
            raise ValueError("ident 不能为空")

        # 使用唯一 logger 名称，避免不同实例之间共享 handler
        super().__init__(name=f"{category}.{ident}", level=level)

        self._category = category
        self._ident = ident
        self._formatter = logging.Formatter(LOG_FORMAT)
        self._context_filter = _ContextFilter(category, ident)

        # 不向 root logger 传播，避免重复输出
        self.propagate = False

        # 默认输出到 stdout
        self.add_output(sys.stdout)

    @property
    def category(self) -> str:
        """日志类别。"""
        return self._category

    @property
    def ident(self) -> str:
        """日志标识。"""
        return self._ident

    def add_output(
        self,
        target: Union[str, IO[str], logging.Handler],
        level: Optional[Union[int, str]] = None,
    ) -> logging.Handler:
        """添加新的日志输出源。

        :param target: 输出目标，支持三种形式:

            - ``str``: 文件路径，创建 :class:`logging.FileHandler`；
            - 文件对象（如 ``sys.stderr``），创建 :class:`logging.StreamHandler`；
            - :class:`logging.Handler` 实例，直接使用。

        :param level: 该输出源的最低日志级别，默认跟随 logger 级别。
        :returns: 被添加的 handler，便于后续移除。
        """
        if isinstance(target, logging.Handler):
            handler = target
        elif isinstance(target, str):
            handler = logging.FileHandler(target, encoding="utf-8")
        elif hasattr(target, "write"):
            handler = logging.StreamHandler(target)
        else:
            raise TypeError(f"不支持的输出目标类型: {type(target)!r}")

        handler.setFormatter(self._formatter)
        handler.addFilter(self._context_filter)
        if level is not None:
            handler.setLevel(level)
        self.addHandler(handler)
        return handler

    def remove_output(self, handler: logging.Handler) -> None:
        """移除指定的输出源。"""
        self.removeHandler(handler)
        handler.close()


plugin_logger = LoggerBase(category="framework", ident="plugin-loader")
