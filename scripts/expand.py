"""expand_ui 等价实现：展开缓存树中某个节点的直接子节点（渐进披露）。"""
import argparse
import sys

from common import load_state, init_uia, eprint


def main():
    init_uia()
    p = argparse.ArgumentParser()
    p.add_argument("--ref", required=True, help="缓存中的 @eN 引用")
    args = p.parse_args()

    state = load_state()
    elements = state.get("elements", {})
    node = elements.get(args.ref)
    if not node:
        print("错误：未找到引用 %s（请先 observe）" % args.ref)
        sys.exit(1)

    parent_path = node["path"]
    kids = [n for n in elements.values()
            if len(n["path"]) == len(parent_path) + 1
            and n["path"][:-1] == parent_path]
    kids.sort(key=lambda n: n["path"][-1])

    print("%s [%s] %s 的子节点（%d 个）：" % (
        node["ref"], node["role"], node.get("label") or "", len(kids)))
    for n in kids:
        marker = "▸%d" % n["children_count"] if n["children_count"] else "·"
        aid = n.get("automationId")
        extra = (" #%s" % aid) if aid else ""
        print("  %s [%s] %s %s%s" % (n["ref"], n["role"], n.get("label") or "", marker, extra))
    eprint("expand: %d children" % len(kids))


if __name__ == "__main__":
    main()
