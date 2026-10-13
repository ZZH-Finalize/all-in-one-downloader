# 编程准则

本文档规定了本项目开发过程中需要遵守的编码规范与约定，所有贡献者在提交代码前应当阅读并遵循。

## 1. 日志（Logger）使用规范

- 框架层的 logger 统一在 [`src/log.py`](../src/log.py) 内创建实例。
- 除 [`src/log.py`](../src/log.py) 之外，任何位置**不得**自行创建框架层的 logger 实例（即禁止调用 `logging.getLogger(...)` 或 `logging.Logger(...)` 等方式新建框架层 logger）。
- 其他模块需要记录日志时，只能从 [`src/log.py`](../src/log.py) 导入并使用其中已创建好的 logger 实例。

示例：

```python
# 正确做法
from log import logger

logger.info("任务开始")

# 错误做法：禁止在其他文件中创建框架层 logger
from log import LoggerBase

logger = LoggerBase(category="framework", ident="plugin-loader")  # ❌ 不允许
```

## 2. 代码注释规范

- 代码注释**优先使用中文**，包括模块说明、类与函数的 docstring、行内注释等。
- 注释应清晰表达设计意图与关键逻辑，避免无意义的复述代码。
- 涉及公开接口、协议字段等需要与外部对齐的内容，可在中文注释之外补充英文术语。

## 3. 语法特性与标准库优先原则

- 能够借助 Python 语法特性简洁实现的部分，应尽可能使用语法特性，而不是手写冗长逻辑。例如：
  - 使用推导式（列表/字典/集合推导式）替代显式循环构造容器；
  - 使用 `with` 上下文管理器管理资源；
  - 使用 `dataclass`、`enum`、`functools`、`itertools` 等语言与标准库能力简化代码；
  - 使用类型注解（type hints）提升代码可读性与可维护性。
- 能够调用现成库（标准库或项目已引入的第三方库）实现的功能，**优先调用库**，不要重复造轮子。例如：
  - 路径处理使用 `pathlib` 而非字符串拼接；
  - 数据解析使用 `json`、`re` 等标准库而非手写解析器；
  - 并发与异步任务优先使用 `asyncio`、`concurrent.futures` 等成熟方案。
- 引入新的第三方库前，应先确认标准库或已有依赖无法满足需求，并在提交说明中注明引入理由。
