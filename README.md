# HeylooBot

海络云 AstrBot 运营查询插件，用于通过聊天指令查询指定短链成功数、昨日点击总览和当前队列指标。

## 功能

- 支持 `/点击查询 <URL> <起始日期> <截止日期>` 指令，例如 `/点击查询 ln.run/9dEX9 2026-07-01 2026-07-02`
- 支持 `/昨日点击 <URL>` 指令，自动查询昨天 0 点到今天 0 点之间的成功数
- 支持 `/昨日点击总览` 指令，返回昨日点击统计图片
- 支持 `/当前队列` 指令，同时查询两台队列服务器并返回统计图片
- 异步调用事件日志查询接口，按 URL 和时间范围直接统计 `click-request` 与 `click-success`

## 使用方式

在 AstrBot 会话中发送：

```text
/点击查询 ln.run/9dEX9 2026-07-01 2026-07-02
```

查询完成后会回复类似：

```text
ln.run/9dEX9 在 2026-07-01 00:00:00 到 2026-07-02 00:00:00 成功 87 个
```

查看指定 URL 昨日成功数：

```text
/昨日点击 ln.run/9dEX9
```

该指令会自动计算昨天 0 点到今天 0 点之间的点击。

查看昨日整体点击统计：

```text
/昨日点击总览
```

插件会返回一张统计图片，包含统计周期、总数、成功数、失败数、成功率和失败率。

查看当前队列：

```text
/当前队列
```

插件会返回一张统计图片，包含任务队列数量、事件队列数量和队列 Key。
当前固定查询：

- `http://43.98.192.252:8991/queue-metrics`
- `http://154.217.241.177:8991/queue-metrics`

## 配置

插件支持在 AstrBot 管理面板中配置：

- `event_api_base_url`：打点服务器地址，默认 `http://8.218.63.188:8181`。插件会自动请求 `/api/query`。
- `enable_image_response`：是否启用图片回复，默认开启。关闭后，`/昨日点击总览` 和 `/当前队列` 只返回纯文本，不返回图片。

请优先填写内网或本机地址，不要把服务器直接暴露在公网。

## 数据文件

运行数据优先写入 AstrBot 数据目录：

```text
data/plugin_data/HeylooBot/
```

当前点击计数查询不再生成 `request.json`、`request_meta.json` 或 `record.csv`。

如果本地测试环境无法读取 AstrBot 数据目录，插件会回退到项目内 `data/plugin_data/HeylooBot/`，该目录已加入 `.gitignore`。

## 依赖

```bash
pip install -r requirements.txt
```

当前依赖：

- `aiohttp`：异步网络请求

## 测试

```bash
python3 -m unittest discover -s "tests" -v
python3 -m compileall "main.py" "models" "scripts/extract_url_records.py" "tests/test_click_report.py" "tests/test_image_options.py" "tests/test_plugin_config.py" "tests/test_queue_report.py" "tests/test_response_text.py"
```

提交前建议使用 `ruff` 格式化代码：

```bash
ruff format .
```

## 相关链接

- [AstrBot 项目](https://github.com/AstrBotDevs/AstrBot)
- [AstrBot 插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)
- [AstrBot 发送消息文档](https://docs.astrbot.app/dev/star/guides/send-message.html)
