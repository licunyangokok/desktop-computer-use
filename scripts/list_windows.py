"""find_roots 等价实现：枚举桌面顶层窗口。

pi-computer-use 的 listRoots 返回桌面上的顶层窗口（HWND）森林，
这里用 uiautomation 的桌面根控件的直接子节点枚举，给每个窗口分配
@wN 引用并写入 state 文件，供后续 observe 使用。
"""
import argparse
import sys

import uiautomation as ua

from common import (
    init_uia, load_state, save_state, next_state_id,
    safe_call, safe_attr, dump_json,
)


def is_browser(class_name, name):
    cn = (class_name or "").lower()
    nm = (name or "").lower()
    if "chrome" in cn or "chrome" in nm:
        return True
    if cn in ("mozillawindowclass", "ieframe"):
        return True
    if "edge" in cn or "msedge" in cn:
        return True
    return False


def main():
    init_uia()
    p = argparse.ArgumentParser()
    p.add_argument("--name", default=None, help="按窗口标题模糊过滤（可选）")
    p.add_argument("--only-visible", action="store_true", help="只看可见窗口")
    args = p.parse_args()

    state = load_state()
    root = ua.GetRootControl()
    windows = {}
    roots = []
    idx = 0
    for w in safe_attr(root, "GetChildren") or []:
        hwnd = safe_call(lambda: w.NativeWindowHandle)
        if not hwnd:
            continue
        name = safe_call(lambda: w.Name) or ""
        class_name = safe_call(lambda: w.ClassName) or ""
        if args.only_visible:
            try:
                if not w.IsVisible:
                    continue
            except Exception:
                pass
        if args.name and args.name.lower() not in (name or "").lower():
            continue
        ref = "@w%d" % idx
        idx += 1
        info = {
            "ref": ref,
            "hwnd": int(hwnd),
            "name": name,
            "className": class_name,
            "bounds": safe_call(lambda: None) or None,
            "browser": is_browser(class_name, name),
        }
        try:
            r = w.BoundingRectangle
            info["bounds"] = {"x": r.left, "y": r.top, "w": r.right - r.left, "h": r.bottom - r.top}
        except Exception:
            info["bounds"] = None
        windows[ref] = info
        roots.append(info)

    state["windows"] = windows
    state["stateId"] = next_state_id(state)
    save_state(state)

    print("stateId: %s" % state["stateId"])
    print("找到 %d 个顶层窗口：" % len(roots))
    for w in roots:
        tag = " [浏览器]" if w["browser"] else ""
        b = w.get("bounds")
        bstr = "" if not b else " @(%d,%d) %dx%d" % (b["x"], b["y"], b["w"], b["h"])
        print("  %s %s%s  (hwnd=%s, class=%s)%s" % (
            w["ref"], w["name"] or "<无标题>", tag, w["hwnd"], w["className"], bstr))
    sys.stderr.write("state saved: %s\n" % state["stateId"])


if __name__ == "__main__":
    main()
