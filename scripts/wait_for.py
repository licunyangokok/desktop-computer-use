"""wait_for 等价实现：轮询等待某个 UI 条件成立（或消失）。

复刻 pi-computer-use 的 uiaWaitFor：给定一个窗口，周期性重新抓取元素，
直到满足 query 匹配（默认「出现」）或超时。--inverse 表示等待「消失」。
"""
import argparse
import sys
import time

from common import init_uia, resolve_window, collect_elements, eprint


def collect_text_index(root_ctrl, root_ref, max_nodes=6000):
    elements, _ = collect_elements(root_ctrl, root_ref, max_nodes=max_nodes)
    return elements


def condition_met(elements, query, role):
    for n in elements.values():
        if role and n.get("role") != role:
            continue
        hay = " ".join([
            n.get("role", ""), n.get("label", ""),
            n.get("automationId", ""), n.get("className", ""),
            str(n.get("value", "")),
        ]).lower()
        if query.lower() in hay:
            return True
    return False


def main():
    init_uia()
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, help="窗口引用 @wN")
    p.add_argument("--query", default=None, help="模糊匹配文本/标签/id")
    p.add_argument("--role", default=None, help="按角色匹配，如 button")
    p.add_argument("--timeout", type=float, default=15.0, help="超时秒数")
    p.add_argument("--poll", type=float, default=0.5, help="轮询间隔秒数")
    p.add_argument("--inverse", action="store_true", help="等待条件「消失」而非「出现」")
    args = p.parse_args()

    _, winfo = (None, None)
    # 解析窗口句柄
    from common import load_state
    state = load_state()
    root_ctrl, winfo = resolve_window(state, args.root)

    deadline = time.time() + args.timeout
    while True:
        elements = collect_text_index(root_ctrl, args.root)
        met = condition_met(elements, args.query or "", args.role)
        if args.inverse:
            done = not met
            what = "消失"
        else:
            done = met
            what = "出现"
        if done:
            print("OK: 条件已%s（query=%s, role=%s）" % (what, args.query, args.role))
            sys.exit(0)
        if time.time() > deadline:
            print("TIMEOUT: 在 %.1fs 内条件未%s（query=%s, role=%s）" % (
                args.timeout, what, args.query, args.role))
            sys.exit(2)
        time.sleep(args.poll)


if __name__ == "__main__":
    main()
