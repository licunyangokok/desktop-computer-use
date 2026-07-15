"""read_text 等价实现：读取窗口或元素的文本内容。

pi-computer-use 的 uiaReadText 从元素读取文本。这里：
- --ref  : 读取单个缓存元素的 value/text
- --root : 重新遍历窗口，按文档顺序输出所有含文本的节点（文本/编辑框等）
"""
import argparse
import sys

from common import (
    init_uia, load_state, resolve_window, resolve_element, collect_elements,
    value_of, safe_call,
)


def main():
    init_uia()
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=None, help="窗口引用 @wN（遍历整窗文本）")
    p.add_argument("--ref", default=None, help="元素引用 @eN（读取单元素）")
    p.add_argument("--max-nodes", type=int, default=6000)
    args = p.parse_args()

    state = load_state()

    if args.ref:
        ctrl = resolve_element(state, args.ref)
        print(value_of(ctrl))
        return

    if not args.root:
        print("错误：需要 --root 或 --ref")
        sys.exit(1)

    root_ctrl, _ = resolve_window(state, args.root)
    elements, _ = collect_elements(root_ctrl, args.root, max_nodes=args.max_nodes)
    printed = 0
    for n in sorted(elements.values(), key=lambda x: (len(x["path"]), x["path"])):
        text = (n.get("value") or "").strip()
        name = (n.get("label") or "").strip()
        if not text:
            # 实时重读：很多控件的文本在 Name / Value / Text 之一
            try:
                ctrl = resolve_element(state, n["ref"])
                text = (value_of(ctrl) or "").strip()
                nm = safe_call(lambda: ctrl.Name) or ""
                name = (name or nm).strip()
            except Exception:
                text = ""
        # 优先用 value，否则用 Name（部分控件把文本放在 Name 上）
        out = text or name
        if out:
            printed += 1
            print("[%s:%s] %s" % (n["role"], n.get("label") or "", out))
    sys.stderr.write("read_text: %d 个文本节点\n" % printed)


if __name__ == "__main__":
    main()
