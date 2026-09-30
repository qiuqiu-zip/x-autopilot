#!/usr/bin/env python3
"""
X Auto-pilot via CDP — 全自动化引擎
====================================
通过 Chrome DevTools Protocol 控制 X 的所有操作。
CDP 事件具有 isTrusted: true，与真人操作完全一致。

前提：
- Chrome CDP 实例运行在 :9222（带独立 profile，已登录 X）
- 或启动脚本：chrome --user-data-dir=/tmp/x-cdp-profile --remote-debugging-port=9222

用法：
  python3 cdp_agent.py post "要发的文字"
  python3 cdp_agent.py reply "<post-url>" "回复文字"
  python3 cdp_agent.py like "<post-url>"
  python3 cdp_agent.py follow "<username>"
  python3 cdp_agent.py check          # 检查登录/状态
"""
import json, urllib.request, websocket, time, os, sys, struct, base64, random

CDP_PORT = 9222

def http_json(path, method="GET"):
    req = urllib.request.Request(f"http://127.0.0.1:{CDP_PORT}{path}", method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

class WS:
    def __init__(self, url):
        host, port = "127.0.0.1", CDP_PORT
        path = url.split(str(port), 1)[1]
        self.s = socket.create_connection((host, port), timeout=20)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n".encode())
        resp = b""
        while b"\r\n\r\n" not in resp: resp += self.s.recv(4096)
    def send(self, data):
        h = bytearray([0x81]); n = len(data)
        if n < 126: h.append(0x80|n)
        elif n < 65536: h.append(0x80|126); h += struct.pack(">H", n)
        else: h.append(0x80|127); h += struct.pack(">Q", n)
        mask = os.urandom(4); h += mask
        self.s.sendall(bytes(h) + bytes(b ^ mask[i%4] for i, b in enumerate(data)))
    def _rx(self, n):
        buf = b""
        while len(buf) < n:
            c = self.s.recv(n - len(buf))
            if not c: raise EOFError
            buf += c
        return buf
    def recv(self):
        hdr = self._rx(2); n = hdr[1] & 0x7F
        if n == 126: n = struct.unpack(">H", self._rx(2))[0]
        elif n == 127: n = struct.unpack(">Q", self._rx(8))[0]
        if hdr[1] & 0x80: self._rx(4)
        return self._rx(n)

class CDPAgent:
    def __init__(self):
        self.ws = None; self.cid = 0
        self.connect()
    
    def connect(self):
        tab = http_json("/json/new?https://x.com/home", "PUT")
        ws_url = tab["webSocketDebuggerUrl"]
        self.ws = WS(ws_url) if 'WS' in dir() else None
        if not self.ws:
            self.ws = WS.__new__(WS)
            WS.__init__(self.ws, ws_url)
    
    def cmd(self, method, params=None):
        self.cid += 1; my = self.cid
        self.ws.send(json.dumps({"id": my, "method": method, "params": params or {}}).encode())
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == my: return m.get("result", {})
    
    def ev(self, js):
        r = self.cmd("Runtime.evaluate", {"expression": js, "returnByValue": True})
        v = r.get("result", {}).get("value")
        if v is None and r.get("exceptionDetails"):
            raise RuntimeError(json.dumps(r["exceptionDetails"])[:200])
        return v
    
    def navigate(self, url):
        self.cmd("Page.navigate", {"url": url})
        time.sleep(1)
        for _ in range(15):
            if self.ev("document.readyState") == "complete": break
            time.sleep(1)
        time.sleep(2)
    
    def wait_for(self, selector, timeout=15):
        for _ in range(timeout * 2):
            if self.ev(f'!!document.querySelector("{selector}")'): return True
            time.sleep(0.5)
        return False
    
    def type_text(self, selector, text):
        """用 CDP Input.insertText 输入文本（isTrusted: true）"""
        self.ev(f'document.querySelector("{selector}").focus()')
        time.sleep(0.3)
        # 先清空
        self.cmd("Input.dispatchKeyEvent", {"type": "keyDown", "key": "a", "code": "KeyA", "modifiers": 2})  # Ctrl+A
        self.cmd("Input.dispatchKeyEvent", {"type": "keyUp", "key": "a", "code": "KeyA", "modifiers": 2})
        self.cmd("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Backspace", "code": "Backspace"})
        self.cmd("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Backspace", "code": "Backspace"})
        time.sleep(0.3)
        # 逐字符输入（模拟真人打字）
        for char in text:
            if char == '\n':
                self.cmd("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13})
                self.cmd("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13})
            else:
                self.cmd("Input.insertText", {"text": char})
            time.sleep(random.uniform(0.02, 0.08))  # 随机打字速度
    
    def click(self, selector):
        """用 CDP Input.dispatchMouseEvent 点击元素（isTrusted: true）"""
        self.ev(f'(function(){{ var e = document.querySelector("{selector}"); if (e) {{ e.scrollIntoView({{block:"center"}}); }} }})()')
        time.sleep(0.3)
        rect = self.ev(f'(function(){{ var r = document.querySelector("{selector}").getBoundingClientRect(); return JSON.stringify({{x: r.left + r.width/2, y: r.top + r.height/2}}); }})()')
        r = json.loads(rect)
        x, y = int(r["x"]), int(r["y"])
        # 模拟鼠标移动到目标
        self.cmd("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x - 50, "y": y - 30})
        time.sleep(0.1)
        self.cmd("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
        time.sleep(random.uniform(0.05, 0.15))
        self.cmd("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1})
        self.cmd("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})
    
    def check_login(self):
        self.navigate("https://x.com/home")
        return self.ev('!!document.querySelector(\'[data-testid="AppTabBar_Profile_Link"]\')')
    
    def post(self, text):
        self.navigate("https://x.com/compose/post")
        if not self.wait_for('[data-testid="tweetTextarea_0"]'):
            return "NO_BOX"
        self.type_text('[data-testid="tweetTextarea_0"]', text)
        time.sleep(1)
        btn = self.ev('!!document.querySelector(\'[data-testid="tweetButton"]\')')
        if not btn: return "NO_BTN"
        self.click('[data-testid="tweetButton"]')
        time.sleep(3)
        return "posted"
    
    def like(self, url):
        self.navigate(url)
        time.sleep(3)
        like_btn = self.ev('(function(){ var a = document.querySelector("article[data-testid=\\"tweet\\"] [data-testid=\\"like\\"]"); if (!a) return "NO_BTN"; var r = a.getBoundingClientRect(); return JSON.stringify({x: r.left + r.width/2, y: r.top + r.height/2}); })()')
        if like_btn == "NO_BTN": return "NO_LIKE_BTN"
        r = json.loads(like_btn)
        x, y = int(r["x"]), int(r["y"])
        self.cmd("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
        time.sleep(random.uniform(0.05, 0.15))
        self.cmd("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1})
        self.cmd("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})
        time.sleep(1)
        return "liked"

def main():
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    agent = CDPAgent()
    action = sys.argv[1]
    if action == "check":
        print("登录:", agent.check_login())
    elif action == "post":
        agent.post(sys.argv[2])
        print("posted:", sys.argv[2][:50])
    elif action == "like":
        agent.like(sys.argv[2])
        print("liked:", sys.argv[2])
    else:
        print(f"Unknown action: {action}")

if __name__ == "__main__":
    main()
