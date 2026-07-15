# Desktop Computer Use —— Windows 原生语义化桌面控制

> 让 AI 像人一样「看懂并操作」你的 Windows 桌面：找窗口、读界面、点按钮、填表单、滚页面、读文本、等元素出现，还能直接操控浏览器。
> **不是按坐标盲点屏幕，而是读「无障碍树」精准操作控件。**

---

## 🌟 它和别的自动化工具最大的不同

市面上常见的桌面/浏览器自动化（AutoHotkey、PyAutoGUI、Selenium、Playwright，以及各类「网页操作」技能）要么靠**屏幕坐标**点击，要么**只能控网页**。

本技能走的是 **Windows UI Automation（无障碍树）** 路线——把每个按钮、输入框、菜单都当成「有名字、有类型、能互动」的对象，AI 读的是「这是个叫『确定』的按钮」，而不是一堆像素。

| 对比 | 坐标点击类 | 本技能（语义控制） |
|---|---|---|
| 窗口挪动/分辨率变化 | 必崩，点错地方 | 不受影响 |
| 操作对象 | 像素坐标 | 控件名字 + 类型 |
| 能否控原生桌面应用 | 能但易错 | ✅ 稳定 |
| 能否控浏览器 | 有限 | ✅ 内置 CDP |

**一句话：别人教 AI 用眼睛戳像素，本技能给 AI 一本「控件字典」，懂名字就能精确操作。**

---

## 🚀 能做什么

- **find_roots**：列出当前桌面所有顶层窗口（应用、对话框、弹窗）
- **observe_ui**：观察某个窗口的控件树（首屏折叠，按需深入，不炸 context）
- **search / expand / inspect**：按角色/文字搜控件、展开子树、查看单个元素详情
- **act_ui**：
  - `press` 按钮（自动走「接地阶梯」：Invoke→Toggle→Selection→ExpandCollapse→LegacyIAccessible→坐标兜底，带遮挡检测）
  - `setText` 填表（优先 ValuePattern，回退键盘输入）
  - `typeText` / `keypress` / `scroll` / `drag`（拖拽、滚动、按键）
  - 危险操作（点击/拖拽/键盘输入/批量）**默认需二次确认**，防止误触
- **read_text / wait_for**：读取界面文本；等待某元素出现/消失（适合等页面加载）
- **浏览器 CDP 控制**：launch / navigate / evaluate / screenshot / close（直接驱动 Chrome/Edge 自动化网页）

---

## 🎯 典型场景

- 「帮我在计算器里算 123×456」→ 找窗口→按数字→读结果
- 「把这段内容填进记事本/表单」→ 定位编辑框→setValue
- 「打开某网站，把标题和正文抓回来」→ 浏览器 CDP 直接读 DOM
- 「等这个弹窗出现再点确定」→ wait_for + act_ui
- 自动化 GUI 测试、批量填表、RPA 雏形

---

## 🛡️ 安全与隐私（重点）

- **最小权限**：仅声明「桌面控制 / 本机临时文件 / 本地浏览器调试端口（127.0.0.1，不外连公网）」。
- **不联网、不上传**：脚本不在后台连接任何外部服务器，不回传屏幕或键鼠数据。
- **危险操作二次确认**：点击、拖拽、键盘输入、批量动作必须显式带 `--confirm` 才执行，未确认直接拒绝。
- **免责声明**：使用者自行承担操作后果；作者不对误删/误操作/数据损失负责（详见技能内《免责声明》章节）。

---

## 📋 使用前提

- Windows 10/11 桌面会话（需在本机运行，被操作窗口在 current session）
- Python 3.8+，依赖 `uiautomation / websocket-client / Pillow`（免费、开源）
- 标准 Windows 控件可稳定识别；自绘 UI / 游戏 / DirectX 画面（无障碍树为空）识别不到，需退回坐标方案
- 当前为 **免费版**，先积累口碑；进阶版（批量事务、更多浏览器能力）后续推出

---

## 🔗 开源与署名

- 本技能基于 **pi-computer-use**（MIT，earendil-works / Zane Chee）独立再实现
- 依赖：uiautomation（Apache-2.0）、Pillow（HPND）、websocket-client（Apache-2.0/BSD）
- 许可证文件：见包内 `LICENSE` 与 `THIRD_PARTY_LICENSES.md`

---

## 👤 作者 & 开源

- 作者：**木火晨鸣**
- 开源仓库：https://github.com/licunyangokok/desktop-computer-use
- 基于 pi-computer-use（MIT 协议）独立实现
