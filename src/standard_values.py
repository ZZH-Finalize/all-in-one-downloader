from enum import Enum

__all__ = [
    "CapabilityType",
    "ResourceType",
    "LinkType",
    "Platform",
    "Container",
    "VideoCodec",
    "AudioCodec",
    "TaskStatus",
    "PostProcessOp",
]


class _StrEnum(str, Enum):
    """字符串枚举基类，保证枚举值可直接序列化与比较。"""

    def __str__(self) -> str:
        return self.value


class CapabilityType(_StrEnum):
    """能力类型（docs/top_design.md §6）。

    第一版仅开放六种能力。命令处理能力作为未来扩展预留，
    第一版不进入枚举，插件不得注册。

    注意：能力实例自身的类型由派生类本身表达（如 ParseCap 即为
    解析能力），本枚举仅作为能力注册表与调度索引的键使用
    （plugin_design.md §10）。
    """

    MESSAGE_SOURCE = "message_source"  # 消息源能力（服务型）
    IDENTIFY = "identify"  # 识别能力（任务型）
    PARSE = "parse"  # 解析能力（任务型）
    DOWNLOAD = "download"  # 下载能力（任务型）
    PROBE = "probe"  # 探测能力（任务型）
    POST_PROCESS = "post_process"  # 后处理能力（任务型）


class ResourceType(_StrEnum):
    """资源类型（top_design.md §14.1、§15.1）。

    决定任务的后续处理方式：视频/音频属于媒体任务，
    文件属于文件任务（不做媒体选择与后处理）。
    """

    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"  # 磁力链接、普通文件、压缩包等第一版均视为文件任务


class LinkType(_StrEnum):
    """链接类型（top_design.md §11.6）。

    纯解析结果必须给出链接类型，框架据此选择下载能力。
    """

    HTTP = "http"  # 普通 HTTP/HTTPS 直链
    HLS = "hls"  # m3u8 流媒体
    DASH = "dash"  # DASH 流媒体
    MAGNET = "magnet"  # 磁力链接
    TORRENT = "torrent"  # 种子文件


class Platform(_StrEnum):
    """平台标准值（top_design.md §10.3）。

    仅包含框架明确定义的平台。无法归类的资源不得塞进本枚举，
    任务中可以没有真实平台值，仅保留展示用途的占位说明。
    """

    BILIBILI = "bilibili"
    YOUTUBE = "youtube"
    X = "x"
    REDBOOK = "redbook"


class Container(_StrEnum):
    """容器格式标准值。"""

    MP4 = "mp4"
    MKV = "mkv"
    WEBM = "webm"
    FLV = "flv"
    TS = "ts"
    MP3 = "mp3"
    M4A = "m4a"
    FLAC = "flac"


class VideoCodec(_StrEnum):
    """视频编码标准值。"""

    AVC = "avc"
    HEVC = "hevc"
    AV1 = "av1"
    VP9 = "vp9"


class AudioCodec(_StrEnum):
    """音频编码标准值。"""

    AAC = "aac"
    MP3 = "mp3"
    OPUS = "opus"
    FLAC = "flac"
    AC3 = "ac3"


class TaskStatus(_StrEnum):
    """任务状态（top_design.md §9.3）。"""

    CREATED = "created"  # 已创建
    PARSING = "parsing"  # 解析中
    DOWNLOADING = "downloading"  # 下载中
    PROBING = "probing"  # 探测中
    POST_PROCESSING = "post_processing"  # 后处理中
    ARCHIVING = "archiving"  # 归档中
    COMPLETED = "completed"  # 已完成
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"  # 带警告完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class PostProcessOp(_StrEnum):
    """后处理操作类型（plugin_design.md §25）。

    后处理能力必须按操作类型注册；
    媒体转换与附属文件整理不得混用同一操作类型。
    """

    TRANSCODE = "transcode"  # 媒体转码
    REMUX = "remux"  # 媒体重封装
    SUBTITLE_ORGANIZE = "subtitle_organize"  # 字幕整理
    COVER_ORGANIZE = "cover_organize"  # 封面整理
    METADATA_ORGANIZE = "metadata_organize"  # 元数据整理
