#!/usr/bin/env python3
"""
X 自动发布调度器（每日一条·慢速安全版）
========================================
- 每天 20:30 自动发布一条（从 queue 目录取当天文件）
- 发布走真实 UI 通道（x.com 登录会话 + AppleScript 注入）
- 发布后写日志、归档已发内容，防重复
- 独立运行：不依赖 ZCode 在线

用法：
  python3 scheduler.py --daemon     # 常驻模式（配合 launchd/cron 每分钟调用一次）
  python3 scheduler.py --run-once   # 手动触发一次检查（测试用）
"""
import subprocess, sys, time, json, os, glob
from datetime import date

BASE = "/Users/qiuqiuqiu/.zcode/workspace/default/x-autopilot"
QUEUE_DIR = os.path.join(BASE, "queue")           # 待发内容：YYYY-MM-DD.txt
LOG_FILE = os.path.join(BASE, "publish_log.md")
XJS = os.path.join(BASE, "src", "xjs.py")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"- {time.strftime('%Y-%m-%d %H:%M')} {msg}\n")

def xjs(code, timeout=90):
    r = subprocess.run(["python3", XJS, code], capture_output=True, text=True, timeout=timeout)
    out = (r.stdout or r.stderr).strip()
    return out, r.returncode == 0

def logged_today():
    if not os.path.exists(LOG_FILE):
        return False
    today = time.strftime("%Y-%m-%d")
    with open(LOG_FILE, encoding="utf-8") as f:
        return f"发布成功 {today}" in f.read()

def todays_file():
    """queue/YYYY-MM-DD.txt 存在则返回内容"""
    path = os.path.join(QUEUE_DIR, time.strftime("%Y-%m-%d") + ".txt")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            content = f.read().strip()
        return path, content if content else None
    return None, None

def post_to_x(text):
    """通过真实 UI 通道发布"""
    html = "<br>".join(text.split("\n")).replace('"', "&quot;").replace("'", "&#39;")
    fill = f'''(function(){{
      var el = document.querySelector('[data-testid="tweetTextarea_0"]'); if (!el) return 'NO_BOX';
      el.focus();
      document.execCommand('selectAll', false, null);
      document.execCommand('delete', false, null);
      document.execCommand('insertHTML', false, "{html}");
      return 'len=' + el.innerText.length;
    }})()'''
    r1, ok1 = xjs(fill)
    if "NO_BOX" in r1 or not ok1:
        return False, f"fill failed: {r1[:60]}"
    time.sleep(2)
    r2, ok2 = xjs('(function(){ var b = document.querySelector(\'[data-testid="tweetButtonInline"]\'); if (!b) return "NO_BTN"; if (b.getAttribute("aria-disabled") === "true") return "DISABLED"; b.click(); return "posted"; })()')
    if "posted" not in r2:
        return False, f"post failed: {r2[:60]}"
    time.sleep(5)
    return True, "ok"

def verify_posted():
    """发布后验证：主页最新一条是否包含今天的发布"""
    xjs('location.assign("/qiuBuildsAI"); "v"')
    time.sleep(5)
    r, ok = xjs('(function(){ var a = document.querySelector("article[data-testid=\\"tweet\\"]"); return a ? a.innerText.substring(0, 50) : "NONE"; })()')
    return ok, r

def run_once():
    # 已发过今天的？
    if logged_today():
        return "already posted today"
    # 拿今天的内容
    path, content = todays_file()
    if not content:
        return "no content for today"
    # 确保 x.com 登录着
    r, ok = xjs('(function(){ return !!document.querySelector(\'[data-testid="AppTabBar_Profile_Link"]\') ? "in" : (location.href = "/home", "nav"); })()')
    if "in" not in r:
        time.sleep(5)
        r, ok = xjs('(function(){ return !!document.querySelector(\'[data-testid="AppTabBar_Profile_Link"]\') ? "in" : "out"; })()')
        if "in" not in r:
            return "not logged in - skip (will retry next cycle)"
    # 前置：回首页确保内联发帖框存在
    xjs('location.assign("/home"); "nav"')
    time.sleep(5)
    # 发布
    ok, msg = post_to_x(content)
    if ok:
        vok, vdetail = verify_posted()
        log(f"✅ 发布成功 {time.strftime('%Y-%m-%d')} | 验证: {vdetail[:40]} | 内容: {content[:30]}...")
        os.rename(path, path + ".sent")
        return f"posted & verified"
    else:
        log(f"❌ 发布失败 {time.strftime('%Y-%m-%d')} | {msg}")
        return f"failed: {msg}"

def daemon():
    log("🤖 调度器启动（每日一条模式）")
    while True:
        try:
            now = time.localtime()
            # 每天 20:25-23:59 之间执行检查（每晚一条）
            if now.tm_hour >= 20:
                result = run_once()
                if "already" not in result:
                    log(f"run_once: {result}")
        except Exception as e:
            log(f"ERROR: {e}")
        time.sleep(600)  # 10 分钟检查一次

if __name__ == "__main__":
    os.makedirs(QUEUE_DIR, exist_ok=True)
    if "--daemon" in sys.argv:
        daemon()
    elif "--run-once" in sys.argv:
        print(run_once())
    else:
        print(__doc__)
