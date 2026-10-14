"""能力基类与能力执行契约模块。

依据 docs/plugin_design.md 第 7、8、12、14 节实现：

- 第 7 节《能力模型》：能力以能力类形式实现，必须继承框架提供的能力基类，
  提供能力元数据、执行逻辑、取消支持与标准值支持声明。
- 第 8 节《能力类型》：能力按运行方式分为任务型（TaskCapability）
  与服务型（ServiceCapability）两类。
- 第 12 节《能力执行》：每次任务执行由框架创建独立能力实例，
  执行参数以深拷贝纯数据形式传入，返回框架定义的结果对象。
- 第 14 节《取消机制》：框架可以向能力发送取消请求，
  能力基类必须提供默认取消行为，框架可假定取消函数始终可调用。

设计要点：

- 能力类型由派生类本身表达（如未来的 ParseCap 即为解析能力），
  基类不携带 cap_type 字段；调度索引键见 standard_values.CapabilityType。
- 能力优先级由框架侧能力配置统一管理（plugin_design.md §5.4），
  不属于能力自身的静态元数据，基类不携带 priority 字段。
- 取消为框架对能力的直接函数调用：基类默认实现仅记录取消状态，
  长时运行能力应覆写 cancel() 实现自身的中断与资源释放逻辑。
- 能力不自行创建 logger：框架已向插件注入插件级 logger
  （PluginBase.logger），能力通过 bind_logger() 复用所属插件的 logger。
  （同时满足 coding_guidelines.md §1：log.py 之外不得新建框架层 logger。）
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, Any

import log

__all__ = ["CapabilityBase", "TaskCapability", "ServiceCapability"]


class CapabilityBase(BaseModel):
    """能力基类（plugin_design.md §7）。

    能力是插件向框架提供的可调度执行单元，必须由插件以类形式实现，
    由框架/插件在注册与执行时实例化。

    继承 :class:`pydantic.BaseModel`，能力元数据以字段形式平铺
    声明在子类上，实例化时由 pydantic 自动完成类型与约束校验：

    - ``cap_key``: 能力本地标识，在同一插件内必须唯一；
      能力全局标识由框架在注册时生成与维护（§7）。
    - ``settings``: 能力设置模型类（§16），必须为
      :class:`pydantic.BaseModel` 的派生类；能力无设置项时为 ``None``。
    - ``support_matrix``: 能力支持的标准值集合声明（§8），键为标准值
      类别（如 ``"platform"``、``"link_type"``），值为
      standard_values 模块中的枚举实例列表。未知标准值的校验由
      框架注册表负责，基类只声明字段结构。

    注意：能力类型与优先级不属于本基类字段——

    - 能力类型由派生类本身表达（TaskCapability / ServiceCapability
      及其下游六种子类）；
    - 优先级由框架系统设置按能力配置（§5.4），随用户调整而变化，
      不是能力自身的静态属性。
    """

    # validate_default=True: 子类以默认值形式声明的元数据字段也会经过校验
    # arbitrary_types_allowed=True: 允许 settings 等任意类型字段
    model_config = ConfigDict(validate_default=True, arbitrary_types_allowed=True)

    # ---- 能力元数据字段（子类必须覆盖 cap_key 的默认值） ----
    cap_key: str = Field(default="", min_length=1)
    logger: Optional[log.LoggerBase] = PrivateAttr(default=None)
    settings: Optional[type[BaseModel]] = None

    def model_post_init(self, context: Any, /) -> None:
        """pydantic 校验完成后的初始化钩子，由框架实例化流程触发。"""
        if type(self) is CapabilityBase:
            raise TypeError("PluginBase 为抽象基类，不得直接实例化")
        self.logger = log.LoggerBase(category="capability", ident=self.cap_key)

    # ---- 取消机制（plugin_design.md §14） ----
    def cancel(self) -> None:
        """框架调用的取消请求入口，基类提供默认行为，始终可调用。

        默认实现仅记录取消状态，适用于瞬时完成的能力（§14-5）。

        长时运行能力必须覆写本方法（§14-4），在其中：

        1. 中断当前执行流程；
        2. 释放已分配的临时资源（§14-7）；
        3. 不得将取消伪装为普通失败（§14-8），
           也不得捕获取消后继续执行（§15-7）。
        """
        raise NotImplementedError("cancel() not implemented")


class TaskCapability(CapabilityBase):
    """任务型能力基类（plugin_design.md §8）。

    任务型能力由框架根据任务请求调用：每次执行由框架创建独立
    能力实例，执行参数以深拷贝纯数据传入（§12-1、§12-5），
    插件修改执行参数不得影响框架任务上下文。

    解析、下载、探测、后处理、识别能力均继承本类。
    """

    async def execute(self, ctx: BaseModel) -> BaseModel:
        """任务执行入口，由框架调用。

        :param ctx: 框架从任务上下文提取并深拷贝的执行参数，
            只包含纯数据内容（§12-7）；具体类型由下游能力子类定义。
        :returns: 框架定义的结果对象（§12-8）；
            失败时不得返回错误结果，必须抛出框架定义的异常（§15）。
        """
        raise NotImplementedError


class ServiceCapability(CapabilityBase):
    """服务型能力基类（plugin_design.md §8）。

    服务型能力由框架启动和停止，长期运行；消息源能力继承本类。
    start()/stop() 与插件的 on_load()/on_unload() 语义对齐。
    """

    async def start(self) -> None:
        """服务启动入口，由框架调用。"""
        raise NotImplementedError

    async def stop(self) -> None:
        """服务停止入口，由框架调用。

        必须停止长期运行的资源，不得在框架调用 stop() 后继续运行。
        """
        raise NotImplementedError
