"""browser.py —— 浏览器 CDP 控制（完整复刻 launch/navigate/evaluate）。

复刻 pi-computer-use 的浏览器能力：用 Chrome/Edge 的远程调试端口
（--remote-debugging-port）+ DevTools 协议（WebSocket）控制网页：
  - launch     : 启动带调试端口的浏览器（隔离用户目录，避免动到日常配置）
  - navigate   : Page.navigate 打开网址
  - evaluate   : Runtime.evaluate 执行 JS
  - dom        : 取页面 outerHTML
  - screenshot : Page.captureScreenshot 截图

依赖 websocket-client（沙箱已具备）。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.parse

import websocket  # websocket-client

CHROME_CANDIDATES = [
    r"C:/Program Files\Google\Chrome\Application\chrome.exe",
    r"C:/Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:/Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_browser():
    for c in CHROME_CANDIDATES:
        if os.path.exists(c):
            return c
    which = shutil.which("chrome") or shutil.which("msedge") or shutil.which("google-chrome")
    return which


def get_version(port):
    url = "http://127.0.0.1:%d/json/version" % port
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))


class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=30)
        self._id = 0

    def send(self, method, params=None):
        self._id += 1
        msg = {"id": self._id, "method": method, "params": params or {}}
        self.ws.send(json.dumps(msg))
        while True:
            resp = json.loads(self.ws.recv())
            if resp.get("id") == self._id:
                if "error" in resp:
                    raise RuntimeError("CDP error: %s" % resp["error"])
                return resp.get("result", {})

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def get_target_ws(port):
    """拿到一个 page 类型 target 的 WebSocket（Page/Runtime 等命令必须发到 target 级，
    而不是浏览器级的 webSocketDebuggerUrl）。"""
    url = "http://127.0.0.1:%d/json/list" % port
    with urllib.request.urlopen(url, timeout=5) as r:
        targets = json.loads(r.read().decode("utf-8"))
    for t in targets:
        if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
            return t["webSocketDebuggerUrl"]
    # 没有现成 page，则新建一个
    url2 = "http://127.0.0.1:%d/json/new?%s" % (port, urllib.parse.quote("about:blank"))
    with urllib.request.urlopen(url2, timeout=5) as r:
        t = json.loads(r.read().decode("utf-8"))
    return t["webSocketDebuggerUrl"]


def connect(port):
    return CDP(get_target_ws(port))


def cmd_launch(args):
    browser = find_browser()
    if not browser:
        print(json.dumps({"ok": False, "error": "未找到 Chrome/Edge，请先安装"}))
        sys.exit(1)
    port = args.port
    user_data = os.path.join(os.environ.get("TEMP", "."), "dcu_chrome_profile")
    os.makedirs(user_data, exist_ok=True)
    cmd = [
        browser,
        "--remote-debugging-port=%d" % port,
        "--remote-allow-origins=*",
        "--user-data-dir=%s" % user_data,
        "--no-first-run", "--no-default-browser-check",
        args.url or "about:blank",
    ]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # 等待调试端口就绪
    for _ in range(40):
        try:
            ver = get_version(port)
            print(json.dumps({"ok": True, "port": port,
                              "webSocketDebuggerUrl": ver["webSocketDebuggerUrl"],
                              "browser": browser}))
            return
        except Exception:
            time.sleep(0.25)
    print(json.dumps({"ok": False, "error": "浏览器启动后调试端口未就绪"}))


def cmd_navigate(args):
    cdp = connect(args.port)
    cdp.send("Page.enable")
    res = cdp.send("Page.navigate", {"url": args.url})
    cdp.close()
    print(json.dumps({"ok": True, "url": args.url, "result": res}))


def cmd_evaluate(args):
    cdp = connect(args.port)
    cdp.send("Runtime.enable")
    res = cdp.send("Runtime.evaluate",
                   {"expression": args.expr, "returnByValue": True,
                    "awaitPromise": True})
    cdp.close()
    result = res.get("result", {})
    print(json.dumps({"ok": True, "result": result.get("value")}, ensure_ascii=False))


def cmd_dom(args):
    cdp = connect(args.port)
    cdp.send("Runtime.enable")
    res = cdp.send("Runtime.evaluate",
                   {"expression": "document.documentElement.outerHTML",
                    "returnByValue": True})
    cdp.close()
    val = res.get("result", {}).get("value", "")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(val)
        print(json.dumps({"ok": True, "bytes": len(val), "file": args.out}))
    else:
        print(val)


def cmd_screenshot(args):
    cdp = connect(args.port)
    cdp.send("Page.enable")
    res = cdp.send("Page.captureScreenshot", {"format": "png"})
    cdp.close()
    import base64
    data = base64.b64decode(res["data"])
    out = args.out or os.path.join(os.getcwd(), "screenshot.png")
    with open(out, "wb") as f:
        f.write(data)
    print(json.dumps({"ok": True, "file": out, "bytes": len(data)}))


def cmd_close(args):
    ver = get_version(args.port)
    cdp = CDP(ver["webSocketDebuggerUrl"])
    cdp.send("Browser.close")
    cdp.close()
    print(json.dumps({"ok": True, "port": args.port}))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("launch")
    pl.add_argument("--port", type=int, default=9222)
    pl.add_argument("--url", default="about:blank")
    pl.set_defaults(func=cmd_launch)

    pn = sub.add_parser("navigate")
    pn.add_argument("--port", type=int, default=9222)
    pn.add_argument("--url", required=True)
    pn.set_defaults(func=cmd_navigate)

    pe = sub.add_parser("evaluate")
    pe.add_argument("--port", type=int, default=9222)
    pe.add_argument("--expr", required=True)
    pe.set_defaults(func=cmd_evaluate)

    pd = sub.add_parser("dom")
    pd.add_argument("--port", type=int, default=9222)
    pd.add_argument("--out", default=None)
    pd.set_defaults(func=cmd_dom)

    ps = sub.add_parser("screenshot")
    ps.add_argument("--port", type=int, default=9222)
    ps.add_argument("--out", default=None)
    ps.set_defaults(func=cmd_screenshot)

    pc = sub.add_parser("close")
    pc.add_argument("--port", type=int, default=9222)
    pc.set_defaults(func=cmd_close)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
