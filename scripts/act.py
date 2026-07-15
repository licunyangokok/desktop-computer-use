"""act_ui 等价实现：在窗口上执行语义动作（接地阶梯 + 策略 + 批处理）。

接地阶梯（grounding ladder，复刻 pi-computer-use 的 press 顺序）：
  InvokePattern.Invoke → TogglePattern.Toggle → SelectionItemPattern.Select
  → ExpandCollapsePattern(Expand/Collapse) → LegacyIAccessible.DoDefaultAction
  → 坐标点击（仅当允许原始输入时作为兜底）

策略（policy）：
  --headless : 禁止「原始输入」(坐标点击/拖拽/键盘) 与「置顶前台」，只允许语义动作
  --ax-only  : 同 headless，但更严格——彻底禁止任何原始输入（即使兜底也不行）

批处理（transaction）：
  --batch file.json 读取一个动作数组顺序执行；会对 setText/press 涉及的元素
  在动作前后取一次值，给出 before→after 差异，便于事务校验。
"""
import argparse
import json
import sys

import uiautomation as ua

from common import (
    init_uia, load_state, save_state, resolve_element, resolve_window,
    safe_attr, bounds_of, mouse_drag, keypress_send, eprint,
    EXPAND_COLLAPSED, EXPAND_PARTIALLY, EXPAND_EXPANDED,
    SCROLL_LARGE_INCREMENT, SCROLL_LARGE_DECREMENT, SCROLL_NO_AMOUNT,
)

# 需用户显式确认（--confirm）的「原始输入 / 批量」操作。
# 这类操作会真的去动用户的鼠标、键盘或一次性执行多步，误用后果较重，
# 因此必须带 --confirm 才放行——这迫使调用方（AI）在用户明确同意后才执行。
UNSAFE_ACTIONS = {"click", "drag", "keypress", "typeText"}
# 高危按键：即便带 --confirm 也额外打印醒目警告
DANGEROUS_KEYS = {"alt+f4", "ctrl+shift+esc", "ctrl+alt+del",
                  "ctrl+shift+delete", "win+d", "win+l"}


def _needs_confirm(actions):
    for a in actions:
        if a.get("action") in UNSAFE_ACTIONS:
            return True
    return False


def _dangerous_keypress(actions):
    hits = []
    for a in actions:
        if a.get("action") == "keypress":
            k = (a.get("key") or "").strip().lower().replace(" ", "")
            if k in DANGEROUS_KEYS:
                hits.append(k)
    return hits


def do_press(ctrl, allow_raw):
    iv = safe_attr(ctrl, "GetInvokePattern")
    if iv is not None:
        return iv.Invoke(), "invoke"
    tog = safe_attr(ctrl, "GetTogglePattern")
    if tog is not None:
        return tog.Toggle(), "toggle"
    sel = safe_attr(ctrl, "GetSelectionItemPattern")
    if sel is not None:
        return sel.Select(), "select"
    ec = safe_attr(ctrl, "GetExpandCollapsePattern")
    if ec is not None:
        st = safe_attr(ec, "ExpandCollapseState")
        if st in (EXPAND_COLLAPSED, EXPAND_PARTIALLY):
            return ec.Expand(), "expand"
        return ec.Collapse(), "collapse"
    lia = safe_attr(ctrl, "GetLegacyIAccessiblePattern")
    if lia is not None:
        return lia.DoDefaultAction(), "legacyDefaultAction"
    if not allow_raw:
        raise RuntimeError("press: 语义 Pattern 均不可用，且策略禁止原始输入")
    r = bounds_of(ctrl)
    if r["w"] <= 0 or r["h"] <= 0:
        raise RuntimeError("press: 元素无有效坐标，无法回退到点击")
    ua.Click(r["x"] + r["w"] // 2, r["y"] + r["h"] // 2)
    return True, "click-fallback"


def do_set_text(ctrl, value, allow_raw):
    vp = safe_attr(ctrl, "GetValuePattern")
    if vp is not None:
        return vp.SetValue(value), "valuePattern"
    if not allow_raw:
        raise RuntimeError("setText: 无 ValuePattern 且策略禁止原始输入")
    try:
        ctrl.Click()
    except Exception:
        pass
    ua.SendKeys("{Ctrl}a")
    ua.SendKeys(value)
    return True, "sendkeys-fallback"


def do_type_text(ctrl, value, allow_raw):
    if not allow_raw:
        raise RuntimeError("typeText 为原始键盘输入，当前策略禁止")
    try:
        ctrl.Click()
    except Exception:
        pass
    ua.SendKeys(value)
    return True, "sendkeys"


def do_keypress(ctrl, key, allow_raw):
    if not allow_raw:
        raise RuntimeError("keypress 为原始键盘输入，当前策略禁止")
    safe_attr(ctrl, "SetFocus")
    ua.SendKeys(keypress_send(key))
    return True, "sendkeys"


def do_scroll(ctrl, direction, times, allow_raw):
    sp = safe_attr(ctrl, "GetScrollPattern")
    if sp is not None:
        if direction in ("down", "up"):
            v = SCROLL_LARGE_INCREMENT if direction == "down" else SCROLL_LARGE_DECREMENT
            h = SCROLL_NO_AMOUNT
        else:
            h = SCROLL_LARGE_INCREMENT if direction == "right" else SCROLL_LARGE_DECREMENT
            v = SCROLL_NO_AMOUNT
        ok = True
        for _ in range(max(1, times)):
            ok = sp.Scroll(h, v) and ok
        return ok, "scrollPattern"
    if not allow_raw:
        raise RuntimeError("scroll: 无 ScrollPattern 且策略禁止原始输入")
    r = bounds_of(ctrl)
    cx = r["x"] + r["w"] // 2
    cy = r["y"] + r["h"] // 2
    for _ in range(max(1, times)):
        if direction in ("down", "up"):
            ua.WheelDown() if direction == "down" else ua.WheelUp()
        else:
            # 横向滚动：用带 Shift 的滚轮
            ua.SendKeys("{Shift}{%s}" % ("Down" if direction == "right" else "Up"))
    return True, "wheel-fallback"


def do_click_ref(ctrl, allow_raw):
    if not allow_raw:
        raise RuntimeError("click 为原始坐标输入，当前策略禁止")
    r = bounds_of(ctrl)
    if r["w"] <= 0 or r["h"] <= 0:
        raise RuntimeError("click: 元素无有效坐标")
    cx = r["x"] + r["w"] // 2
    cy = r["y"] + r["h"] // 2
    ua.Click(cx, cy)
    return True, "click"


def do_click_xy(x, y, allow_raw):
    if not allow_raw:
        raise RuntimeError("click 为原始坐标输入，当前策略禁止")
    # 遮挡检测：点击点最顶层元素应当就是目标（这里仅做点击）
    ua.Click(int(x), int(y))
    return True, "click"


def do_drag(x1, y1, x2, y2, allow_raw):
    if not allow_raw:
        raise RuntimeError("drag 为原始坐标输入，当前策略禁止")
    mouse_drag(x1, y1, x2, y2)
    return True, "drag"


def snapshot_value(state, eref):
    try:
        ctrl = resolve_element(state, eref)
        vp = safe_attr(ctrl, "GetValuePattern")
        if vp is not None:
            try:
                return vp.Value
            except Exception:
                pass
        t = safe_attr(ctrl, "GetText")
        return t if isinstance(t, str) else ""
    except Exception:
        return "<unresolved>"


def run_one(state, a, allow_raw):
    action = a.get("action")
    ref = a.get("ref")
    ctrl = None
    if ref:
        ctrl = resolve_element(state, ref)
    if action == "press":
        ok, method = do_press(ctrl, allow_raw)
    elif action == "setText":
        ok, method = do_set_text(ctrl, a.get("value", ""), allow_raw)
    elif action == "typeText":
        ok, method = do_type_text(ctrl, a.get("value", ""), allow_raw)
    elif action == "keypress":
        ok, method = do_keypress(ctrl, a.get("key", ""), allow_raw)
    elif action == "scroll":
        ok, method = do_scroll(ctrl, a.get("direction", "down"), int(a.get("times", 1)), allow_raw)
    elif action == "click":
        if ref:
            ok, method = do_click_ref(ctrl, allow_raw)
        else:
            ok, method = do_click_xy(a.get("x"), a.get("y"), allow_raw)
    elif action == "drag":
        ok, method = do_drag(a.get("x1"), a.get("y1"), a.get("x2"), a.get("y2"), allow_raw)
    else:
        return {"action": action, "ok": False, "error": "未知动作: %s" % action}
    return {"action": action, "ref": ref, "ok": bool(ok), "method": method}


def main():
    init_uia()
    p = argparse.ArgumentParser()
    p.add_argument("--ref", default=None)
    p.add_argument("--action", default=None)
    p.add_argument("--value", default=None)
    p.add_argument("--key", default=None)
    p.add_argument("--direction", default="down")
    p.add_argument("--times", type=int, default=1)
    p.add_argument("--x", type=int, default=None)
    p.add_argument("--y", type=int, default=None)
    p.add_argument("--x1", type=int, default=None)
    p.add_argument("--y1", type=int, default=None)
    p.add_argument("--x2", type=int, default=None)
    p.add_argument("--y2", type=int, default=None)
    p.add_argument("--batch", default=None, help="批处理 JSON 文件路径")
    p.add_argument("--headless", action="store_true", help="禁止原始输入/置顶")
    p.add_argument("--ax-only", action="store_true", help="彻底禁止原始输入")
    p.add_argument("--confirm", action="store_true",
                   help="危险/原始输入操作（click/drag/keypress/typeText/批量）需显式确认后才执行")
    args = p.parse_args()

    allow_raw = not (args.headless or args.ax_only)

    # 批量模式
    if args.batch:
        with open(args.batch, "r", encoding="utf-8") as f:
            actions = json.load(f)
        if _needs_confirm(actions) and not args.confirm:
            print(json.dumps({
                "ok": False,
                "error": "拒绝执行：批量动作含原始输入/危险操作，需先向用户复述计划并取得明确同意后，"
                         "再带 --confirm 重新调用。",
            }, ensure_ascii=False))
            sys.exit(1)
        dk = _dangerous_keypress(actions)
        if dk:
            eprint("⚠️ 警告：批量动作包含高危按键 %s，确认用户已明确同意再继续。" % dk)
        state = load_state()
        results = []
        diffs = []
        for a in actions:
            ref = a.get("ref")
            before = snapshot_value(state, ref) if ref else None
            res = run_one(state, a, allow_raw)
            after = snapshot_value(state, ref) if ref else None
            if before is not None and before != after:
                diffs.append({"ref": ref, "before": before, "after": after})
            results.append(res)
        out = {"results": results}
        if diffs:
            out["diffs"] = diffs
        print(json.dumps(out, ensure_ascii=False))
        return

    if not args.action:
        print(json.dumps({"ok": False, "error": "需要 --action 或 --batch"}))
        sys.exit(1)

    a = {
        "ref": args.ref,
        "action": args.action,
        "value": args.value,
        "key": args.key,
        "direction": args.direction,
        "times": args.times,
        "x": args.x, "y": args.y,
        "x1": args.x1, "y1": args.y1, "x2": args.x2, "y2": args.y2,
    }
    if _needs_confirm([a]) and not args.confirm:
        print(json.dumps({
            "ok": False,
            "error": "拒绝执行：%s 属于原始输入/危险操作，需先向用户复述计划并取得明确同意后，"
                     "再带 --confirm 重新调用。" % a["action"],
        }, ensure_ascii=False))
        sys.exit(1)
    dk = _dangerous_keypress([a])
    if dk:
        eprint("⚠️ 警告：操作包含高危按键 %s，确认用户已明确同意再继续。" % dk)
    state = load_state()
    before = snapshot_value(state, args.ref) if args.ref else None
    res = run_one(state, a, allow_raw)
    after = snapshot_value(state, args.ref) if args.ref else None
    if before is not None and before != after:
        res["before"] = before
        res["after"] = after
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
