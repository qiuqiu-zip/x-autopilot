#!/usr/bin/env python3
"""Reply to a post on X via the logged-in Chrome session (real UI channel).

Usage:
  python3 reply_tweet.py "<post-url-or-permalink>" "<reply text>"

Example:
  python3 reply_tweet.py "https://x.com/dotey/status/123" "Great breakdown!"

Prerequisite:
  Chrome is open on any x.com page, logged in, with
  View > Developer > Allow JavaScript from Apple Events enabled.
"""
import subprocess, sys, time, json, re

XJS = __file__.rsplit("/", 1)[0] + "/xjs.py"

def xjs(code, timeout=90):
    r = subprocess.run(['python3', XJS, code], capture_output=True, text=True, timeout=timeout)
    out = (r.stdout or r.stderr).strip()
    if r.returncode != 0:
        raise RuntimeError(out[:200])
    return out

def main():
    if len(sys.argv) < 3:
        print('usage: reply_tweet.py "<post-url>" "<text>"'); sys.exit(1)
    url, text = sys.argv[1], sys.argv[2]
    html = '<br>'.join(text.split('\n')).replace('"', '&quot;')

    xjs(f'location.assign("{url}"); "go"')
    time.sleep(6)

    # 打开回复框（帖子页直接有内联回复框）
    state = xjs('''(function(){
      var el = document.querySelector('[data-testid="tweetTextarea_0"]');
      if (!el) {
        var rb = document.querySelector('article [data-testid="reply"]');
        if (!rb) return 'NO_BOX';
        rb.click();
      }
      return 'ready';
    })()''')
    if state != 'ready':
        time.sleep(3)

    fill = '''(function(){
      var el = document.querySelector('[data-testid="tweetTextarea_0"]'); if (!el) return 'NO_BOX';
      el.focus();
      document.execCommand('selectAll', false, null);
      document.execCommand('delete', false, null);
      document.execCommand('insertHTML', false, "__HTML__");
      return 'len=' + el.innerText.length;
    })()'''.replace('__HTML__', html)
    print('fill:', xjs(fill))
    time.sleep(1.5)

    r = xjs('''(function(){
      var b = document.querySelector('[data-testid="tweetButton"]') || document.querySelector('[data-testid="tweetButtonInline"]');
      if (!b) return 'NO_BTN';
      if (b.getAttribute('aria-disabled') === 'true') return 'DISABLED';
      b.click(); return 'posted';
    })()''')
    print('post:', r)
    time.sleep(4)
    print('done')

if __name__ == '__main__':
    main()
