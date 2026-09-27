import json, subprocess, sys
js = sys.argv[1]
applescript = f'''
tell application "Google Chrome"
  repeat with w from 1 to count of windows
    repeat with t from 1 to count of tabs of window w
      if URL of tab t of window w contains "x.com" then
        return execute tab t of window w javascript {json.dumps(js, ensure_ascii=False)}
      end if
    end repeat
  end repeat
end tell'''
r = subprocess.run(['osascript', '-e', applescript], capture_output=True, text=True)
if r.returncode != 0:
    print("ERR:", r.stderr.strip(), file=sys.stderr)
    sys.exit(1)
print(r.stdout.strip())
