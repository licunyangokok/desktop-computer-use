"""search_ui 等价实现：在最近一次 observe 缓存的元素里按条件检索。"""
import argparse
import sys

from common import load_state, eprint


def matches(node, role, label, query):
    if role and node.get("role") != role:
        return False
    if label and node.get("label") != label:  # 精确
        # 也允许子串
        if label.lower() not in (node.get("label") or "").lower():
            return False
    if query:
        hay = " ".join([
            node.get("role", ""),
            node.get("label", ""),
            node.get("automationId", ""),
            node.get("className", ""),
            node.get("value", ""),
        ]).lower()
        if query.lower() not in hay:
            return False
    return True


def main():
    init_uia = __import__("common").init_uia
    init_uia()
    p = argparse.ArgumentParser()
    p.add_argument("--query", default=None, help="在 role/label/automationId/className/value 中模糊匹配")
    p.add_argument("--role", default=None, help="按语义角色精确过滤，如 button/edit")
    p.add_argument("--label", default=None, help="按标签过滤（精确，失败则子串）")
    p.add_argument("--state", default=None, help="指定 stateId（默认用当前 state）")
    p.add_argument("--limit", type=int, default=40)
    args = p.parse_args()

    state = load_state()
    if args.state and state.get("stateId") != args.state:
        eprint("警告：请求的 state=%s 与当前 state=%s 不一致" % (args.state, state.get("stateId")))
    elements = state.get("elements", {})
    results = [n for n in elements.values() if matches(n, args.role, args.label, args.query)]
    results.sort(key=lambda n: n["ref"])
    print("stateId: %s  匹配 %d 个（显示前 %d）：" % (state.get("stateId"), len(results), args.limit))
    for n in results[: args.limit]:
        aid = n.get("automationId")
        extra = (" #%s" % aid) if aid else ""
        print("  %s [%s] %s %s" % (n["ref"], n["role"], n.get("label") or "", extra))
    sys.stderr.write("search: %d matched\n" % len(results))


if __name__ == "__main__":
    main()
