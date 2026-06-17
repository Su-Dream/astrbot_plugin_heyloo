功能需经过测试。
需包含良好的注释。
持久化数据请存储于 data 目录下，而非插件自身目录，防止更新/重装插件时数据被覆盖。
良好的错误处理机制，不要让插件因一个错误而崩溃。
在进行提交前，请使用 ruff 工具格式化您的代码。
不要使用 requests 库来进行网络请求，可以使用 aiohttp, httpx 等异步网络请求库。
事件监听器可以收到平台下发的消息内容，可以实现指令、指令组、事件监听等功能。
事件监听器的注册器在 astrbot.api.event.filter 下，需要先导入。请务必导入，否则会和 python 的高阶函数 filter 冲突。
from astrbot.api.event import filter, AstrMessageEvent
