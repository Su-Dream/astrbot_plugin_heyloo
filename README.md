# HeylooBot

海络云 AstrBot 运营查询插件，用于通过聊天指令查询指定短链昨日点击记录，并导出点击明细 CSV。

## 功能

- 支持 `/昨日点击 <URL片段>` 指令，例如 `/昨日点击 ln.run/miTyN`
- 支持 `/昨日点击总览` 指令，返回昨日点击统计图片
- 支持 `/当前队列` 指令，返回任务队列和事件队列统计图片
- 收到指令后先回复 `查询中`
- 异步调用事件日志查询接口，支持较长等待时间
- 同一天内复用已保存的 `request.json`，跨天自动重新查询并覆盖
- 将接口原始响应保存为 `request.json`
- 调用 `scripts/extract_url_records.py` 筛选成功和失败点击记录
- 生成并发送 `record.csv`
- 回复成功点击数和失败点击数汇总

## 使用方式

在 AstrBot 会话中发送：

```text
/昨日点击 ln.run/miTyN
```

插件会回复：

```text
查询中
```

查询完成后会回复：

```text
查找到ln.run/miTyN成功点击x个,失败点击x个;点击明细如下
```

同时发送 `record.csv` 文件。

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

## 数据文件

运行数据优先写入 AstrBot 数据目录：

```text
data/plugin_data/HeylooBot/
```

主要文件：

- `request.json`：接口返回的原始响应
- `request_meta.json`：记录 `request.json` 对应的查询日期
- `record.csv`：按 URL 片段筛选后的点击明细

例如 6 月 17 日查询的是 6 月 16 日数据，插件会在 6 月 17 日当天复用同一份 `request.json`；到了 6 月 18 日会重新查询 6 月 17 日数据并覆盖旧文件。

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
python3 -m compileall "main.py" "models" "scripts/extract_url_records.py" "tests/test_click_report.py" "tests/test_queue_report.py"
```

提交前建议使用 `ruff` 格式化代码：

```bash
ruff format .
```

## 相关链接

- [AstrBot 项目](https://github.com/AstrBotDevs/AstrBot)
- [AstrBot 插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)
- [AstrBot 发送消息文档](https://docs.astrbot.app/dev/star/guides/send-message.html)
