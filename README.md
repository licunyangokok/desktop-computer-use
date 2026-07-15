# desktop-computer-use

> 让 AI 像人一样"看懂"并操作 Windows 桌面应用与浏览器——不靠坐标截图，而是读取无障碍树（UIA）做语义化控制。

## 这是什么

`desktop-computer-use` 是一个 Windows 桌面自动化技能。它让 AI 助手能够：

- **语义化操作**：通过 Windows UI Automation（UIA）读取界面结构，用"按钮名称 / 控件角色"而非像素坐标来点击、输入、选择。
- **双通道控制**：既控制原生桌面应用（计算器、记事本、系统设置等），也通过 Chrome DevTools Protocol（CDP）控制浏览器。
- **安全优先**：危险操作（关闭窗口、系统快捷键组合）必须二次确认；全程本地运行，不联网、不上传任何数据。

## 为什么不一样（核心亮点）

传统桌面自动化靠"截图 + 坐标点击"，界面布局一变就失效。`desktop-computer-use` 读取的是**无障碍树**——界面元素的结构化描述，相当于给 AI 一份带标签的清单。这种方式对界面微调更稳定，也更接近"人"理解界面的方式（看到"确定"按钮就点，而不是记死它在屏幕的哪个像素）。

## 安装

要求 Python 3.8+，在技能目录下执行：

```bash
pip install -r requirements.txt
```

依赖：`uiautomation`、`websocket-client`、`Pillow`（协议与署名详见 `THIRD_PARTY_LICENSES.md`）。

## 使用

在支持该技能的 AI 助手中，用自然语言触发即可，例如：

- "帮我打开计算器并算一下 1+1"
- "自动把这个表单填好并提交"
- "用浏览器打开某网站并截图"

技能内置以下工具（`scripts/` 目录下，供 AI 调用）：

| 工具 | 作用 |
|---|---|
| `find_roots` | 列出当前桌面窗口 |
| `observe` | 读取某窗口/区域的无障碍树 |
| `search` | 按关键词在界面中找控件 |
| `expand` | 展开折叠的界面区域 |
| `inspect` | 查看某个控件的详细属性 |
| `act` | 执行操作（点击 / 输入 / 按键，危险操作需 `--confirm`） |
| `read_text` | 读取控件文本内容 |
| `wait_for` | 等待某个界面状态出现 |
| `browser` | 浏览器 CDP 控制（启动 / 导航 / 求值 / 截图） |

## 原创性声明

本技能为基于开源项目 **pi-computer-use**（`earendil-works/pi`，MIT License）的 **Python 独立再实现**，并非逐行复制上游源码，依 MIT 协议保留原作者版权声明。第三方依赖的许可证见 `THIRD_PARTY_LICENSES.md`。

## 许可

MIT License © 2026 木火晨鸣

## 注意事项

- 仅支持 Windows 系统。
- 操作本机应用需由用户主动触发并授权。
- 危险操作（如关闭窗口、系统快捷键）会要求二次确认。
- 全程本地运行，不连接公网、不上传任何数据。

## 作者 & 开源

- 作者：**木火晨鸣**
- 开源仓库：https://github.com/licunyangokok/desktop-computer-use
- 基于 [pi-computer-use](https://github.com/earendil-works/pi)（MIT 协议）独立实现，版权与署名详见《开源协议与署名》章节。
