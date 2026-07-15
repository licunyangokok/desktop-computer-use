"""desktop-computer-use 公共模块

提供：
- uiautomation 初始化
- UIA ControlType 语义 role 映射（复用 pi-computer-use 的语义化思路）
- 元素 capabilities（支持的 UIA Pattern）探测
- 跨进程 ref 存储与解析（state 文件 + 路径/运行时ID 回解）
- 坐标拖拽 / 滚动 / 按键等原语
- state 文件读写

本模块被各脚本复用。所有脚本均以 venv 内的 python 运行，uiautomation 已安装。
"""
import os
import sys
import json
import time
import ctypes
import tempfile

import uiautomation as ua

# 技能目录（scripts 的上一级）
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# state 文件放在系统临时目录，而不是技能目录内——
# 这样发布技能时不会把使用者本机的窗口句柄等运行期数据一并打包出去。
STATE_PATH = os.path.join(tempfile.gettempdir(), "desktop_computer_use.state.json")

# UIA ScrollAmount 枚举（用于 ScrollPattern.Scroll）
SCROLL_LARGE_DECREMENT = 0
SCROLL_SMALL_DECREMENT = 1
SCROLL_NO_AMOUNT = 2
SCROLL_SMALL_INCREMENT = 3
SCROLL_LARGE_INCREMENT = 4

# ExpandCollapseState 枚举
EXPAND_COLLAPSED = 0
EXPAND_EXPANDED = 1
EXPAND_PARTIALLY = 2
EXPAND_LEAF = 3


def init_uia():
    """初始化 UI Automation COM 环境。"""
    try:
        ua.InitializeUIAutomation()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# state 文件读写
# ---------------------------------------------------------------------------
def load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"stateId": None, "windows": {}, "elements": {}}


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def next_state_id(state):
    cur = state.get("stateId")
    if not cur:
        return "s1"
    try:
        n = int(cur[1:]) + 1
    except Exception:
        n = 1
    return "s%d" % n


# ---------------------------------------------------------------------------
# 语义 role 映射
# ---------------------------------------------------------------------------
def role_of(ctrl):
    """把 UIA ControlTypeName（如 'ButtonControl'）转成语义 role（如 'button'）。

    等价于 pi-computer-use Rust 端 control_type_to_role() 的语义化目标，
    只是这里直接用可读名字，避免维护一长串整型常量。
    """
    try:
        name = ctrl.ControlTypeName
    except Exception:
        name = ""
    if name.endswith("Control"):
        name = name[: -len("Control")]
    if not name:
        return "unknown"
    return name[0].lower() + name[1:]


def bounds_of(ctrl):
    try:
        r = ctrl.BoundingRectangle
        return {
            "x": r.left,
            "y": r.top,
            "w": r.right - r.left,
            "h": r.bottom - r.top,
        }
    except Exception:
        return {"x": 0, "y": 0, "w": 0, "h": 0}


def safe_call(fn):
    try:
        return fn()
    except Exception:
        return None


def safe_attr(ctrl, attr):
    """安全获取控件的方法并调用。

    关键：uiautomation 的 Pattern 获取方法（GetInvokePattern / GetValuePattern 等）
    只存在于特定子类（ButtonControl / EditControl …），基类 Control 没有。
    因此不能用 `safe_call(ctrl.GetXxx)`（会在传参时因 AttributeError 直接崩），
    而要用 getattr 先判断是否存在再调用。
    """
    fn = getattr(ctrl, attr, None)
    if fn is None:
        return None
    try:
        return fn()
    except Exception:
        return None


def detect_capabilities(ctrl):
    """探测元素支持哪些 UIA Pattern（对应 pi 的 capabilities）。"""
    caps = {}
    for name, method in [
        ("invoke", "GetInvokePattern"),
        ("toggle", "GetTogglePattern"),
        ("value", "GetValuePattern"),
        ("expandCollapse", "GetExpandCollapsePattern"),
        ("selectionItem", "GetSelectionItemPattern"),
        ("scroll", "GetScrollPattern"),
        ("legacyIAccessible", "GetLegacyIAccessiblePattern"),
    ]:
        caps[name] = safe_attr(ctrl, method) is not None
    return caps


def value_of(ctrl):
    vp = safe_attr(ctrl, "GetValuePattern")
    if vp is not None:
        try:
            return vp.Value
        except Exception:
            pass
    t = safe_attr(ctrl, "GetText")
    return t if isinstance(t, str) else ""


def build_node(ctrl, ref, window_ref, path, depth):
    """从 live Control 抽取一个可序列化的节点描述。"""
    children = safe_attr(ctrl, "GetChildren") or []
    return {
        "ref": ref,
        "window_ref": window_ref,
        "path": list(path),
        "depth": depth,
        "runtimeId": safe_attr(ctrl, "GetRuntimeId") or [],
        "role": role_of(ctrl),
        "label": safe_call(lambda: ctrl.Name) or "",
        "automationId": safe_call(lambda: ctrl.AutomationId) or "",
        "className": safe_call(lambda: ctrl.ClassName) or "",
        "value": value_of(ctrl),
        "bounds": bounds_of(ctrl),
        "enabled": bool(safe_call(lambda: ctrl.IsEnabled) or False),
        "keyboardFocusable": bool(safe_call(lambda: ctrl.IsKeyboardFocusable) or False),
        "capabilities": detect_capabilities(ctrl),
        "children_count": len(children),
    }


def collect_elements(ctrl, window_ref, max_nodes=4000, max_depth=999):
    """遍历 UIA 子树，返回 {ref: node} 字典（按发现顺序编号 @e0, @e1, ...）。"""
    elements = {}
    root_rid = safe_call(ctrl.GetRuntimeId) or []

    def recurse(c, path, depth):
        if len(elements) >= max_nodes or depth > max_depth:
            return
        ref = "@e%d" % len(elements)
        node = build_node(c, ref, window_ref, path, depth)
        elements[ref] = node
        for i, ch in enumerate(safe_call(c.GetChildren) or []):
            recurse(ch, path + [i], depth + 1)

    recurse(ctrl, [], 0)
    return elements, root_rid


# ---------------------------------------------------------------------------
# ref 解析（跨进程：脚本每次独立运行，靠 state 文件回解）
# ---------------------------------------------------------------------------
def _control_from_handle_retry(hwnd, retries=4):
    """ControlFromHandle 对 UWP 等窗口偶发 COMError，重试几次。"""
    for _ in range(retries):
        try:
            c = ua.ControlFromHandle(hwnd)
            if c is not None:
                return c
        except Exception:
            pass
        time.sleep(0.2)
    return None


def _find_window_by_hwnd(hwnd):
    """兜底：从桌面根的直接子节点里按 NativeWindowHandle 找窗口控件。"""
    try:
        root = ua.GetRootControl()
        for w in safe_attr(root, "GetChildren") or []:
            try:
                if w.NativeWindowHandle == hwnd:
                    return w
            except Exception:
                pass
    except Exception:
        pass
    return None


def resolve_window(state, wref):
    w = state.get("windows", {}).get(wref)
    if not w:
        raise KeyError("unknown window ref: %s" % wref)
    hwnd = w["hwnd"]
    ctrl = _control_from_handle_retry(hwnd)
    if ctrl is None:
        ctrl = _find_window_by_hwnd(hwnd)
    if ctrl is None:
        raise RuntimeError(
            "窗口引用 %s 已失效（窗口可能已关闭或被重建），"
            "请重新运行 list_windows 获取新的 @wN 后再 observe" % wref)
    return ctrl, w


def _walk_find_by_rid(ctrl, target):
    if safe_call(ctrl.GetRuntimeId) == target:
        return ctrl
    for c in safe_call(ctrl.GetChildren) or []:
        r = _walk_find_by_rid(c, target)
        if r is not None:
            return r
    return None


def _match_cached(ctrl, el):
    """判断 live 控件是否与缓存元素身份一致（按稳定属性）。"""
    aid = safe_call(lambda: ctrl.AutomationId) or ""
    if el.get("automationId") and aid and aid == el.get("automationId"):
        return True
    lbl = safe_call(lambda: ctrl.Name) or ""
    if el.get("label") and lbl and lbl == el.get("label") and role_of(ctrl) == el.get("role"):
        return True
    return False


def _semantic_find(ctrl, el):
    """整棵子树按 automationId/label+role 语义搜索（应对控件树重排）。"""
    if _match_cached(ctrl, el):
        return ctrl
    for c in safe_attr(ctrl, "GetChildren") or []:
        r = _semantic_find(c, el)
        if r is not None:
            return r
    return None


def resolve_element(state, eref):
    """把 state 中的 @eN 回解为 live Control。

    解析顺序（兼顾速度与稳健）：
      1) 路径索引快速定位 → 若身份匹配即采用；
      2) 按 runtimeId 整树搜索（pi 的 RuntimeId 兜底）；
      3) 按 automationId / label+role 语义搜索（应对 UWP 等控件树重排、
         索引漂移的情况，最稳健）。
    """
    el = state.get("elements", {}).get(eref)
    if not el:
        raise KeyError("unknown element ref: %s" % eref)
    root_ctrl, _ = resolve_window(state, el["window_ref"])

    # 1) 路径索引
    cur = root_ctrl
    ok = True
    for idx in el["path"]:
        children = safe_attr(cur, "GetChildren") or []
        if idx >= len(children):
            ok = False
            break
        cur = children[idx]
    if ok and cur is not None and _match_cached(cur, el):
        return cur

    # 2) runtimeId 兜底
    target_rid = el.get("runtimeId")
    if target_rid:
        found = _walk_find_by_rid(root_ctrl, target_rid)
        if found is not None and _match_cached(found, el):
            return found

    # 3) 语义兜底（最稳健）
    found = _semantic_find(root_ctrl, el)
    if found is not None:
        return found

    raise RuntimeError("元素已消失（UI 发生变化）: %s" % eref)


# ---------------------------------------------------------------------------
# 动作原语
# ---------------------------------------------------------------------------
def mouse_drag(x1, y1, x2, y2, steps=24):
    """用 SendInput 等价方式做鼠标拖拽（ctypes 直接调用 user32）。"""
    ME_MOVE = 0x0001
    ME_LDOWN = 0x0002
    ME_LUP = 0x0004
    user32 = ctypes.windll.user32
    user32.SetCursorPos(int(x1), int(y1))
    user32.mouse_event(ME_LDOWN, 0, 0, 0, 0)
    for i in range(1, steps + 1):
        nx = int(x1 + (x2 - x1) * i / steps)
        ny = int(y1 + (y2 - y1) * i / steps)
        user32.SetCursorPos(nx, ny)
        time.sleep(0.008)
    user32.mouse_event(ME_LUP, 0, 0, 0, 0)


def keypress_send(key):
    """把 'enter' / 'ctrl+c' / 'alt+tab' 之类的描述转成 uiautomation.SendKeys 语法。"""
    special = {
        "enter": "{Enter}",
        "return": "{Enter}",
        "escape": "{Esc}",
        "esc": "{Esc}",
        "tab": "{Tab}",
        "space": "{Space}",
        "backspace": "{BackSpace}",
        "delete": "{Delete}",
        "up": "{Up}",
        "down": "{Down}",
        "left": "{Left}",
        "right": "{Right}",
        "home": "{Home}",
        "end": "{End}",
        "f1": "{F1}",
        "f2": "{F2}",
        "f3": "{F3}",
        "f4": "{F4}",
        "f5": "{F5}",
        "f6": "{F6}",
        "f7": "{F7}",
        "f8": "{F8}",
        "f9": "{F9}",
        "f10": "{F10}",
        "f11": "{F11}",
        "f12": "{F12}",
    }
    if "+" in key:
        mod, _, k = key.partition("+")
        mod = mod.strip().lower()
        k = k.strip().lower()
        mod_token = {"ctrl": "{Ctrl}", "control": "{Ctrl}", "alt": "{Alt}", "shift": "{Shift}", "win": "{Win}"}[mod]
        # 单字符按键
        if k in special:
            return mod_token + special[k]
        return mod_token + k.lower()
    if key.lower() in special:
        return special[key.lower()]
    return key


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------
def eprint(*args):
    """打印到 stderr（用于进度/诊断），避免污染 stdout 的结构化结果。"""
    print(*args, file=sys.stderr)


def dump_json(obj):
    print(json.dumps(obj, ensure_ascii=False))


if __name__ == "__main__":
    init_uia()
    print("common module loaded OK")
