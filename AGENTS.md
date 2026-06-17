# AGENTS.md

本文件记录 astrbot_plugin_heyloo 的开发约定。修改插件时请优先遵守这里的项目规则。

## 基本原则

- 功能变更必须经过测试验证。
- 代码应保持简单直接，避免不必要的抽象和过度设计。
- 关键逻辑需要包含清晰注释，注释语言应与现有代码保持一致。
- 需要有良好的错误处理，不能让插件因为单个请求、单条数据或单次解析失败而整体崩溃。
- 不要主动执行 git commit、git push、创建分支等操作，除非用户明确要求。

## AstrBot 开发约定

- 事件监听器可以接收平台下发的消息内容，可用于实现指令、指令组和事件监听。
- AstrBot 事件过滤器位于 `astrbot.api.event.filter`。
- 导入事件过滤器时必须显式使用 AstrBot 的 `filter`，避免与 Python 内置高阶函数 `filter` 混淆。

推荐导入方式：

```python
from astrbot.api.event import AstrMessageEvent, filter
```

消息发送请优先使用 AstrBot 官方消息组件和事件返回方法，例如 `event.plain_result(...)`、`event.chain_result(...)`。

## 数据持久化

- 持久化数据必须存储在 AstrBot 的 data 目录下，不要存储在插件源码目录中，避免插件更新或重装时数据被覆盖。
- 本项目运行数据应写入 `data/plugin_data/HeylooBot/`。
- 本地测试环境无法读取 AstrBot data 路径时，可以回退到项目内 `data/`，但该目录不得提交到仓库。
- 写入重要运行文件时优先使用临时文件，校验通过后再覆盖正式文件，避免半截文件污染缓存。

## 网络请求

- 不要使用 `requests` 进行网络请求。
- 优先使用 `aiohttp`、`httpx` 等异步网络请求库。
- 网络请求必须设置合理超时。
- 大响应应避免一次性读入内存，优先流式写入文件。
- 生产接口或长耗时接口需要考虑重试和用户可理解的错误提示。

## 测试与质量

- 新增或修改功能时，应同步补充测试。
- 查询、筛选、计数、缓存等核心逻辑必须具备可单独测试的函数。
- 提交前运行测试：

```bash
python3 -m unittest discover -s "tests" -v
python3 -m compileall "main.py" "models" "scripts/extract_url_records.py" "tests/test_click_report.py" "tests/test_image_options.py" "tests/test_queue_report.py"
```

- 提交前使用 ruff 格式化代码：

```bash
ruff format .
```

如果当前环境没有安装 `ruff`，需要在最终说明中明确告知。
