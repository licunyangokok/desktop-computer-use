---
slug: desktop-computer-use
displayName: Desktop Computer Use
name: desktop-computer-use
description: Windows 语义化桌面控制：让 AI 像人一样看懂并操作桌面应用与浏览器。
summary: Windows 语义化桌面控制：让 AI 像人一样看懂并操作桌面应用与浏览器，原生 GUI 与浏览器 CDP 双支持。
version: 1.0.4
author: 木火晨鸣
license: MIT
platforms: [Windows]
pricing: 免费
category: 自动化工具
repository: https://github.com/licunyangokok/desktop-computer-use
homepage: https://github.com/licunyangokok/desktop-computer-use
trigger:
  - 自动操作电脑
  - 桌面自动化
  - 自动点按钮填表
  - 操作 Windows 应用
  - 自动化 GUI
permission:
  - 桌面控制（读取/操作本机窗口与控件，仅限用户主动触发的语义操作）
  - 文件系统访问（仅本技能运行所需状态文件，存于系统临时目录）
  - 本地浏览器调试端口通信（仅连 127.0.0.1 的 Chrome/Edge 远程调试端口，不外连公网、不上传任何数据）
dependency:
  - Python 3.8+
  - uiautomation >= 2.0.29
  - websocket-client >= 1.8.0
  - Pillow >= 10.0.0
---

# Desktop Computer Use（Windows 语义化桌面控制）

## 这是什么（用大白话讲）

普通「自动操作电脑」脚本是按屏幕**坐标**点来点的（比如「点 (100,200)」），窗口一挪就全错。
本技能走的是 **UI Automation 无障碍树**路线：把每个按钮、输入框、菜单都当成「有名字、有类型、能互动」的对象，
AI 读的是「这是个叫『确定』的按钮」，而不是一堆像素。稳定得多，也更像人在操作。

> 大白话类比：坐标点击像「闭着眼戳屏幕第 3 行第 2 列」；语义控制像「伸手去按写着『确定』的那个键」。

## 它能不能「方便操作电脑」？能，但有前提

- ✅ 标准 Windows 软件（设置、计算器、记事本、资源管理器、Office、浏览器、带标准控件的业务系统）都能稳定识别与操作。
- ✅ 不需要被测软件配合，也不用提前录制脚本，打开就能用。
- ⚠️ 自绘 UI / 游戏 / 用 DirectX 画的界面（无障碍树是空的）识别不到——这类只能退回到「坐标 + 截图」方案。
- ⚠️ 必须在**你本机的 Windows 桌面会话**里运行（沙箱即你的真实桌面），且被操作的窗口要在当前会话。

## 原理（与 pi-computer-use 一致）

1. **观察（observe）**：用 Windows UI Automation 读取窗口的无障碍树，把每个控件映射成语义角色
   （button / edit / checkbox / combobox / window …），分配 `@eN` 引用，写入 `state` 文件。
2. **渐进披露**：首屏只给「根 + 直接子节点」，深层用 `search` / `expand` / `inspect` 再看，避免信息爆炸。
3. **动作（act）**：`press` 走「接地阶梯」——先试 Invoke，不行试 Toggle/Select/ExpandCollapse/LegacyIAccessible，
   最后才回退到坐标点击（且仅在允许原始输入时）。编辑框用 ValuePattern 直接设值，比模拟键盘更稳。
4. **策略**：`--headless` 禁止「坐标点击/拖拽/键盘」与置顶，`--ax-only` 更严格彻底禁原始输入，只留语义动作。
5. **浏览器**：单独用 Chrome/Edge 的远程调试端口 + DevTools 协议（WebSocket）控制网页。

## 环境准备（首次使用）

依赖需装在使用本技能的 Python 环境里（`uiautomation` / `websocket-client` / `Pillow`）。
若缺失，在该环境的 python 下执行（**必须是已装好上述依赖的那个解释器**）：

```
python -m pip install -r requirements.txt
```

> 提示：在 WorkBuddy 里请使用它自带的 venv Python（即 WorkBuddy 内置解释器）；在其他环境自行替换为对应解释器。
> **技能本身不含任何写死路径**，放在任意目录、用任意合规 python 都能跑。

## 触发场景（用户说这些话时应启用本技能）

- "帮我自动操作电脑 / 桌面自动化"
- "自动点那个按钮、填一下这个表单"
- "操作一下某某软件 / Windows 应用"
- "让 AI 帮我点界面 / 自动化 GUI"
- "把这个窗口里的数据读出来 / 等某个弹窗出现"
- "用浏览器自动打开某网站、填表、截图"

> 等价于 `pi-computer-use` 的桌面控制能力，但用 Python 实现、零编译、可跨 WorkBuddy / QClaw / ima / Claude Code / Cursor 等环境使用。

## 标准工作流（请严格按此循环）

```
1) find_roots        → 找到目标窗口，拿到 @wN
2) observe_ui @wN    → 读界面，拿到 @eN（只看首屏折叠）
3) search/expand/inspect → 定位到要操作的具体元素
4) act_ui            → 执行 press / setText / keypress / scroll / click / drag
5) read_text / wait_for → 读取结果或等待某元素出现/消失
（循环 2-5 直到任务完成；界面变化后重新 observe）
```

## 调用方式（脚本都在 `scripts/` 下，用「已装依赖的 python」跑）

把下面变量换成你自己的路径（**技能本身不含任何写死路径**，放任意位置均可）：

```
PY = 你环境里已安装 uiautomation 的 python 解释器（如 WorkBuddy 自带 venv 的 python.exe）
SK = 本技能目录下的 scripts 文件夹
```

### 1. find_roots（枚举顶层窗口）
```
$PY $SK/list_windows.py                  # 列出所有顶层窗口
$PY $SK/list_windows.py --name 计算器    # 按标题过滤
```
输出形如 `@w0 计算器 (ApplicationFrameWindow) (hwnd=...)`，记下你要的 `@wN`。

### 2. observe_ui（读界面）
```
$PY $SK/observe.py --root @w0            # 折叠首屏：根 + 直接子节点
$PY $SK/observe.py --root @w0 --full     # 打印完整树（节点多时慎用）
```

### 3. 定位元素
```
$PY $SK/search.py --query 确定           # 在所有元素里模糊搜
$PY $SK/search.py --role button          # 只搜按钮
$PY $SK/expand.py --ref @e3              # 展开 @e3 的直接子节点
$PY $SK/ui_inspect.py --ref @e5             # 看 @e5 的全部属性
$PY $SK/ui_inspect.py --ref @e5 --json      # JSON 详情
```

### 4. act_ui（操作）
```
# 点击/按按钮（语义优先）
$PY $SK/act.py --ref @e5 --action press
# 填表（优先用 ValuePattern 直接设值）
$PY $SK/act.py --ref @e8 --action setText --value "你好"
# 在已聚焦框里追加输入
$PY $SK/act.py --ref @e8 --action typeText --value "abc"
# 按键
$PY $SK/act.py --ref @e8 --action keypress --key enter
$PY $SK/act.py --ref @e8 --action keypress --key ctrl+a
# 滚动
$PY $SK/act.py --ref @e8 --action scroll --direction down --times 3
# 坐标点击 / 拖拽（原始输入，headless/ax-only 下被禁）
$PY $SK/act.py --x 100 --y 200 --action click
$PY $SK/act.py --x1 10 --y1 10 --x2 200 --y2 200 --action drag
# ⚠️ 原始输入/危险操作（click/drag/keypress/typeText 及批量）受 --confirm 门禁保护：
#    先向用户复述计划并取得明确同意，再带 --confirm 重新调用，否则会被拒绝。
$PY $SK/act.py --ref @e8 --action keypress --key enter --confirm
$PY $SK/act.py --x 100 --y 200 --action click --confirm
$PY $SK/act.py --batch actions.json --confirm
# 策略
$PY $SK/act.py --ref @e5 --action press --headless
$PY $SK/act.py --ref @e5 --action press --ax-only
# 批处理（事务）
# 把下面 JSON 存成 actions.json 后执行：
# [{"ref":"@e5","action":"press"},{"ref":"@e8","action":"setText","value":"你好"}]
$PY $SK/act.py --batch actions.json
```

### 5. read_text / wait_for
```
$PY $SK/read_text.py --root @w0          # 读出窗口所有文本
$PY $SK/read_text.py --ref @e5           # 读单个元素文本
$PY $SK/wait_for.py --root @w0 --query 完成 --timeout 20   # 等到「完成」出现
$PY $SK/wait_for.py --root @w0 --query 加载中 --inverse --timeout 20  # 等到「加载中」消失
```

### 6. 浏览器 CDP（完整复刻）
```
$PY $SK/browser.py launch --url https://example.com --port 9222
$PY $SK/browser.py navigate --port 9222 --url https://example.com
$PY $SK/browser.py evaluate --port 9222 --expr "document.title"
$PY $SK/browser.py dom --port 9222 --out page.html
$PY $SK/browser.py screenshot --port 9222 --out shot.png
$PY $SK/browser.py close --port 9222        # 关闭该调试浏览器实例
```
> 说明：launch 已自动加上 `--remote-allow-origins=*` 与隔离的 `--user-data-dir`，
> 不会动到你日常使用的浏览器配置；测试完用 `close` 关掉调试实例即可。

## 开源协议与署名

本技能基于 [pi-computer-use](https://github.com/earendil-works/pi)（上游 `earendil-works/pi` 采用 **MIT 协议**）的设计思路，用 Python **独立重新实现**，并非逐行复制其源码。

- **上游项目**：`pi-computer-use` / `earendil-works/pi` — MIT License
- **核心依赖及协议**：
  - `uiautomation`（yinkaisheng）— Apache-2.0
  - `websocket-client` — Apache-2.0 / BSD
  - `Pillow` — HPND

依照 MIT 协议要求，本技能保留对上游作者及依赖项目的署名与版权声明。
架构层面的「状态作用域引用（state-scoped refs）/ 接地阶梯（grounding ladder）/ 渐进披露（progressive disclosure）」属于通用设计思路，不受版权限制，可自由复刻。

## 重要注意事项

- **必须在你本机 Windows 桌面会话运行**，被操作窗口要在当前用户会话里。
- **操作前先 observe，操作后若界面变了要重新 observe**；`@eN` 是「状态内」引用，界面刷新后旧引用可能失效（脚本会自动按 runtimeId 兜底回解，失效则报错让你重 observe）。
- **headless / ax-only 会禁止坐标点击与键盘输入**，只做语义动作——适合不能被「抢前台」的场景。
- **原始输入类操作（click / drag / keypress / typeText 及批量）有 `--confirm` 门禁**：未带该参数会被拒绝执行。调用前必须先向用户复述将要做什么、并取得明确同意，再带 `--confirm` 调用；对 `alt+f4`、`ctrl+shift+esc` 等高危按键会额外告警。这是保护用户不被误操作的重要机制，请勿绕过。
- 真实点击/输入会**真的去动你的窗口**，执行前确认目标正确；批量动作务必先小范围验证。
- state 文件位于**系统临时目录**的 `desktop_computer_use.state.json`（不在技能目录内，发布技能不会泄漏你的窗口信息），跨脚本共享（每个脚本独立进程，靠它回解引用）。

## 免责声明

1. **使用者自担风险**：本技能会真实操作你本机的窗口、鼠标与键盘。因使用本技能导致的任何数据丢失、文件误删、配置改动、账号误操作或财产损失，**由使用者自行承担，作者与分发平台不承担责任**。执行前请务必确认目标正确，批量/危险操作先小范围验证。
2. **危险操作需确认**：`click` / `drag` / `keypress` / `typeText` 及批量动作受 `--confirm` 门禁保护，调用方（AI）必须先向使用者复述计划并取得明确同意后再执行；对 `alt+f4`、`ctrl+shift+esc` 等高危按键会额外告警。请勿绕过该机制。
3. **不联网、不外传**：本技能所有逻辑均在本地运行，**不会**将屏幕截图、键鼠操作、窗口内容或任何数据上传到任何外部服务器。浏览器控制仅连接你本机启动的调试实例。
4. **适用范围**：仅支持带标准无障碍树（UIA）的 Windows 应用；自绘 UI / 游戏 / DirectX 界面无法识别。请在合法合规的范围内使用，不得用于绕过他人系统安全、自动化刷量或任何违反平台规则的行为。
5. **无担保**：本技能按「现状」提供，不保证对所有软件、所有 Windows 版本均可用，作者不承诺持续维护或即时修复所有缺陷。
