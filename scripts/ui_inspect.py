"""inspect_ui 等价实现：打印某个缓存节点的完整详情。"""
import argparse
import json
import sys

from common import load_state, init_uia


def main():
    init_uia()
    p = argparse.ArgumentParser()
    p.add_argument("--ref", required=True, help="缓存中的 @eN 引用")
    p.add_argument("--json", action="store_true", help="以 JSON 输出完整节点")
    args = p.parse_args()

    state = load_state()
    node = state.get("elements", {}).get(args.ref)
    if not node:
        print("错误：未找到引用 %s（请先 observe）" % args.ref)
        sys.exit(1)

    if args.json:
        print(json.dumps(node, ensure_ascii=False, indent=2))
        return

    print("引用: %s" % node["ref"])
    print("角色: %s" % node["role"])
    print("标签: %s" % (node.get("label") or "<空>"))
    print("AutomationId: %s" % (node.get("automationId") or "<空>"))
    print("ClassName: %s" % (node.get("className") or "<空>"))
    print("值: %r" % (node.get("value") or ""))
    b = node.get("bounds") or {}
    print("坐标: x=%s y=%s w=%s h=%s" % (b.get("x"), b.get("y"), b.get("w"), b.get("h")))
    print("可用: %s  可键盘聚焦: %s" % (node.get("enabled"), node.get("keyboardFocusable")))
    print("子节点数: %s" % node.get("children_count"))
    caps = node.get("capabilities") or {}
    on = [k for k, v in caps.items() if v]
    print("能力(Pattern): %s" % (", ".join(on) if on else "<无>"))


if __name__ == "__main__":
    main()
