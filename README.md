# Silence Guard

让 agent 的 `<silence>` 真的安静下来。

一个极小的 AstrBot 插件：当整条回复只有一个静默占位符时，直接丢弃它——不发送、不提示、不占用任何输出。

## 为什么需要它

很多「群聊潜水」类人设会在系统提示词里约定：没有必要时回复 `<silence>`。

但 **AstrBot 核心并没有实现这个约定**。它不认识 `<silence>`，只会把模型返回的文本原样发出去，于是群里就经常出现一条孤零零的 `<silence>`。

常见的替代方案是把它加进「内容安全 → 屏蔽词」，但那个方案有三个问题：

1. 屏蔽词默认只检查**入站消息**，要生效必须手动开启 `content_safety.also_use_in_response`
2. 开启后，**流式输出会整段跳过检查**（`result_decorate` 里的 `and not is_stream`）
3. 最关键的是语义不对：屏蔽词命中是**整条拒收 + 播报一句 `Your message or the model response contains inappropriate content and has been blocked.`**

也就是说，模型每沉默一次，用户就会收到一句英文拦截通知。这不是静默，是打扰。

本插件做的是真正的静默：命中即 `clear_result()`，什么都不会发生。

## 工作原理

插件只挂一个事件——`OnDecoratingResultEvent`（发送消息前）：

```python
@filter.on_decorating_result()
async def drop_silence(self, event: AstrMessageEvent):
    result = event.get_result()
    ...
    if is_silence(text):
        event.clear_result()
```

`clear_result()` 把结果置空后，`result_decorate` 阶段会因 `not result.chain` 提前返回，消息不会被发送，也不会触发任何提示。

## 匹配规则

整条回复**去掉首尾空白后恰好等于**下列之一时丢弃（大小写不敏感）：

| 写法 | 说明 |
|---|---|
| `<silence>` | 标准写法 |
| `<silence>` 带换行 / 首尾空格 | 容忍模型多打了空白 |
| `< silence >` | 容忍尖括号内的空格 |
| `<slience>` | 常见手滑拼写 |
| `[silence]` | 方括号变体 |

对应正则在 `main.py` 的 `SILENCE_PATTERNS` 里，想加自己的写法直接往列表里追加即可。

## 以下情况会原样放行

- 占位符混在长句里，例如 `我先回个 <silence> 试试`
- 回复包含图片、语音、视频、文件等媒体成分
- 结果链为空

只有「整条回复就是一个占位符」才会被丢弃，避免误杀正常内容。

## 安装

把仓库放进 AstrBot 的插件目录：

```bash
git clone https://github.com/MomoiaMoia/astrbot_plugin_silence_guard \
  data/plugins/astrbot_plugin_silence_guard
```

然后重启 AstrBot 让插件被扫描加载（容器部署的话 `docker restart <容器名>` 最稳妥）。

> 注意：AstrBot 加载插件依赖同目录的 `metadata.yaml`（**只认 `.yaml` / `.yml`，不认 `.json`**），缺失会导致加载失败。

无第三方依赖，不需要额外 `pip install`。

## 验证

加载成功后日志会输出：

```
[silence_guard] 已加载，静默占位符模式: 3 条
```

发送 `/silence_check` 可确认插件在位。

之后每当有条回复被静默丢弃，日志会记录一行：

```
[silence_guard] 丢弃静默回复: '<silence>'
```

聊天窗口里不会有任何消息。

## 注意事项

- **流式输出**：`OnDecoratingResultEvent` 在流式结束时同样会触发，但此时文本已经逐段吐出去了，`clear_result()` 撤不回来。想要完全静默，建议关闭 `provider_settings.streaming_response`
- **与屏蔽词冲突**：内容安全检查在插件 hook **之前**执行。如果屏蔽词列表里还留着 `<silence>`，会先被它拦下并播报英文提示，静默逻辑根本跑不到。请确保把它从屏蔽词里移除
- **只处理文本**：本插件不判断回复是不是 LLM 产生的，任何来源的纯文本整条命中都会丢弃（包括插件指令的回复）

## 文件结构

```
astrbot_plugin_silence_guard/
├── main.py          # 全部逻辑，约 70 行
├── metadata.yaml    # 插件元信息
├── README.md
└── LICENSE
```

## 许可

AGPL-3.0

---

来自：神秘蓝色小女仆
