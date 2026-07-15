"""observe_ui 等价实现：抓取某个窗口的语义 UI 树（state-scoped）。

流程（复刻 pi-computer-use 的 look/observe）：
1. 从 state 中的 @wN 窗口解析出 live Control；
2. 递归遍历整棵 UIA 子树，给每个元素分配 @eN 引用并写入 state；
3. 打印「折叠首屏」：只给根 + 直接子节点（带子节点数量标记），
   深层节点通过 expand_ui / search_ui 再展开（渐进披露）。
"""
import argparse
import sys

from common import (
    init_uia, load_state, save_state, next_state_id,
    resolve_window, collect_elements, eprint, role_of,
)


def print_folded(elements, root_ref):
    """打印折叠视图：根节点 + 直接子节点。"""
    root = next((n for n in elements.values() if n["path"] == []), None)
    if root is None:
        print("(无根节点)")
        return
    b = root.get("bounds") or {}
    bstr = " @(%d,%d) %dx%d" % (b.get("x", 0), b.get("y", 0), b.get("w", 0), b.get("h", 0)) if b else ""
    print("%s [%s] %s%s" % (root["ref"], root["role"], root.get("label") or "<root>", bstr))
    # 直接子节点：path 长度为 1
    children = [n for n in elements.values() if n["path"] and len(n["path"]) == 1]
    children.sort(key=lambda n: n["path"][0])
    for n in children:
        marker = "▸%d" % n["children_count"] if n["children_count"] else "·"
        label = n.get("label") or ""
        aid = n.get("automationId")
        extra = (" #%s" % aid) if aid else ""
        print("  %s [%s] %s %s%s" % (n["ref"], n["role"], label, marker, extra))
    print("— 共发现 %d 个元素（含折叠）。用 expand_ui / search_ui 查看深层。" % len(elements))


def main():
    init_uia()
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, help="state 中的窗口引用，如 @w0")
    p.add_argument("--max-nodes", type=int, default=4000)
    p.add_argument("--max-depth", type=int, default=999)
    p.add_argument("--full", action="store_true", help="打印完整树（不折叠）")
    args = p.parse_args()

    state = load_state()
    root_ctrl, winfo = resolve_window(state, args.root)
    elements, _ = collect_elements(
        root_ctrl, args.root, max_nodes=args.max_nodes, max_depth=args.max_depth
    )

    sid = next_state_id(state)
    # 更新窗口信息（可能窗口标题变了）
    winfo["name"] = safe_name(root_ctrl)
    state["windows"][args.root] = winfo
    state["stateId"] = sid
    state["elements"] = elements
    save_state(state)

    print("stateId: %s  (root=%s)" % (sid, args.root))
    if args.full:
        print_full(elements, args.root)
    else:
        print_folded(elements, args.root)
    sys.stderr.write("observe done: %d elements, state %s\n" % (len(elements), sid))


def safe_name(ctrl):
    try:
        return ctrl.Name
    except Exception:
        return ""


def print_full(elements, root_ref):
    # 按 path 排序后缩进打印整棵树
    nodes = sorted(elements.values(), key=lambda n: (len(n["path"]), n["path"]))
    # 建立 path->缩进层级映射
    for n in nodes:
        depth = len(n["path"])
        indent = "  " * depth
        marker = "▸%d" % n["children_count"] if n["children_count"] else "·"
        label = n.get("label") or ""
        print("%s%s [%s] %s %s" % (indent, n["ref"], n["role"], label, marker))


if __name__ == "__main__":
    main()
