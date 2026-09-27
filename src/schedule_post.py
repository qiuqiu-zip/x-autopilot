#!/usr/bin/env python3
"""Schedule a post on X via the logged-in Chrome session (native scheduler).

Usage:
  python3 schedule_post.py "<text>" <month-name> <day> <year> <hour24> <minute>

Example:
  python3 schedule_post.py "Hello future!" October 8 2026 20 30

Prerequisite:
  Chrome is open on any x.com page, logged in, with
  View > Developer > Allow JavaScript from Apple Events enabled.
"""
import subprocess, sys, time, json

XJS = __file__.rsplit("/", 1)[0] + "/xjs.py"

def xjs(code, timeout=90):
    r = subprocess.run(['python3', XJS, code], capture_output=True, text=True, timeout=timeout)
    out = (r.stdout or r.stderr).strip()
    if r.returncode != 0:
        raise RuntimeError(out[:200])
    return out

SET_SELECTS = '''(function(){
  var dlg = document.querySelector('[role="dialog"]');
  if (!dlg) return JSON.stringify({err: 'no dialog'});
  var sels = dlg.querySelectorAll('select');
  if (sels.length < 5) return JSON.stringify({err: 'selects=' + sels.length});
  var targets = __TARGETS__;
  var setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
  var report = [];
  for (var i = 0; i < 5; i++) {
    var sel = sels[i]; var hit = null;
    Array.from(sel.options).forEach(function(o){
      if (hit === null && (o.text === targets[i] || o.text.replace(/^0/, '') === targets[i] || o.value === targets[i])) hit = o.value;
    });
    if (hit === null) { report.push(i + ':MISS(' + targets[i] + ')'); continue; }
    setter.call(sel, hit);
    sel.dispatchEvent(new Event('change', {bubbles: true}));
    report.push(i + ':' + sel.selectedOptions[0].text);
  }
  return JSON.stringify(report);
})()'''

def main():
    if len(sys.argv) < 7:
        print('usage: schedule_post.py "<text>" <MonthName> <day> <year> <hour24> <minute>'); sys.exit(1)
    text = sys.argv[1]
    month, day, year = sys.argv[2], int(sys.argv[3]), sys.argv[4]
    hour, minute = sys.argv[5], sys.argv[6]
    html = '<br>'.join(text.split('\n')).replace('"', '&quot;')

    xjs('location.assign("/compose/post"); "nav"')
    time.sleep(6)

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

    print('open scheduler:', xjs('(function(){ var b = document.querySelector(\'[data-testid="scheduleOption"]\'); if (!b) return "NO_BTN"; b.click(); return "ok"; })()'))
    time.sleep(3)

    # 轮询等待下拉框渲染
    r3 = '{"err":"not-ready"}'
    for _ in range(6):
        r3 = xjs(SET_SELECTS.replace('__TARGETS__', json.dumps([month, day, year, hour, minute])))
        if 'selects=0' not in r3 and 'no dialog' not in r3:
            break
        time.sleep(2)
    print('set date:', r3)
    time.sleep(1)

    print('confirm:', xjs('(function(){ var d = document.querySelector(\'[role="dialog"]\'); if (!d) return "NO_DIALOG"; var b = d.querySelector(\'[data-testid="scheduledConfirmationPrimaryAction"]\'); if (!b) return "NO_CONFIRM"; b.click(); return "confirmed"; })()'))
    time.sleep(3)
    print('done')

if __name__ == '__main__':
    main()
