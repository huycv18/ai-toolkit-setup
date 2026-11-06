"""Cài Windows-MCP, Ponytail, Headroom cho Claude Code, Codex (GPT), Gemini trên máy Windows.

  check  so máy với danh sách, không sửa gì; exit 1 nếu còn thiếu
  apply  cài phần còn thiếu (idempotent), rồi kiểm lại toàn bộ
"""
import json, os, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HOME = Path.home()
BIN = HOME / ".local" / "bin"
TOOLS = HOME / "AppData" / "Roaming" / "uv" / "tools"
PLUGINS = HOME / ".claude" / "plugins"
CODEX = HOME / ".codex"
GEMINI = HOME / ".gemini"
PROXY = "http://127.0.0.1:8787"

UV_TOOLS = [  # (tên env, spec, python); headroom cần đúng 3.13, đổi bản sẽ làm uv xóa env đang chạy
    ("windows-mcp", "windows-mcp", None),
    ("headroom-ai", "headroom-ai[proxy,code,mcp]", "3.13"),
]
MARKETS = {"ponytail": "https://github.com/dietrichgebert/ponytail.git",
           "headroom-marketplace": "https://github.com/headroomlabs-ai/headroom.git"}
PLUGIN_IDS = ["ponytail@ponytail"]
# Plugin headroom chỉ có hook "headroom init hook ensure" mỗi lần gọi Bash: bật profile init-user tranh cổng 8787
# với codex-local (3.531 lần khởi động trên máy Huy) và bật cửa sổ console. Proxy đã có task riêng nên gỡ (2026-11-06).
HR_PLUGIN = "headroom@headroom-marketplace"
HR_TASK = "ai-toolkit-headroom-codex"  # task tự bật proxy ẩn khi đăng nhập và mỗi 5 phút
MCP = {"windows-mcp": [str(BIN / "windows-mcp.exe"), "serve"]}
CODEX_MCP = {**MCP, "headroom": [str(BIN / "headroom.exe"), "mcp", "serve"]}
# Claude desktop bỏ qua ANTHROPIC_BASE_URL nên proxy chỉ phục vụ Codex (DECISIONS 2026-11-05)
HEADROOM_CODEX = ["install", "apply", "--preset", "persistent-task", "--providers", "manual",
                  "--target", "codex", "--profile", "codex-local", "--port", "8787", "--mode", "cache",
                  "--no-telemetry", "--no-rate-limit", "--code-aware"]
CODEX_PROVIDER = ('[model_providers.headroom]\nname = "OpenAI"\nbase_url = "http://127.0.0.1:8787/v1"\n'
                  'supports_websockets = true\nrequires_openai_auth = true\n')
CODEX_TOP = ['model_provider = "headroom"', 'openai_base_url = "http://127.0.0.1:8787/v1"']


class Skip(Exception):
    """Không áp dụng cho máy này, không tính là lỗi."""


def load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def exe(name):
    p = BIN / f"{name}.exe"
    return str(p) if p.exists() else shutil.which(name)


def codex_exe():
    found = shutil.which("codex")
    if found:
        return found
    apps = sorted((HOME / "AppData" / "Local" / "OpenAI" / "Codex" / "bin").glob("*/codex.exe"),
                  key=lambda p: p.stat().st_mtime)
    return str(apps[-1]) if apps else None


def run(*cmd):
    if not cmd[0]:
        raise RuntimeError(f"không tìm thấy chương trình cho lệnh {cmd[1:3]}")
    print("  $", " ".join(map(str, cmd)))
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip()[-500:])
    return r.stdout


def proxy_ok():
    """Proxy codex-local đang chạy; profile khác (init-user) chiếm cổng thì không tính."""
    try:
        d = json.load(urllib.request.urlopen(PROXY + "/health", timeout=3))
        return d.get("ready") is True and d.get("deployment", {}).get("profile") == "codex-local"
    except Exception:
        return False


def ps(script):
    return run("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script)


def task_ok():
    return subprocess.run(["schtasks", "/Query", "/TN", HR_TASK], capture_output=True).returncode == 0


def do_task():
    """Task đăng nhập + mỗi 5 phút chạy ensure-headroom qua conhost --headless: không có cửa sổ.
    Task health của headroom (InteractiveToken khi máy không cho S4U) chớp cmd mỗi 5 phút nên xóa."""
    ensure = HOME / ".headroom" / "deploy" / "codex-local" / "ensure-headroom.cmd"
    if not ensure.exists():
        raise RuntimeError(f"chưa có {ensure}, cài proxy trước")
    ps(f"""
$ErrorActionPreference = 'Stop'
foreach ($n in 'headroom-codex-local-health', 'headroom-codex-local-startup') {{
    Unregister-ScheduledTask -TaskName $n -Confirm:$false -ErrorAction SilentlyContinue }}
$a = New-ScheduledTaskAction -Execute 'conhost.exe' -Argument '--headless cmd.exe /c "{ensure}"'
$t1 = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$t2 = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)
$s = New-ScheduledTaskSettingsSet -Hidden -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName '{HR_TASK}' -Action $a -Trigger $t1, $t2 -Settings $s -Force | Out-Null
Start-ScheduledTask -TaskName '{HR_TASK}'
""")


def stop_init_user():
    """Tắt proxy init-user (do hook headroom bật) để codex-local lấy lại cổng 8787."""
    ps("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'headroom' -and "
       "$_.CommandLine -match 'init-user' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force "
       "-ErrorAction SilentlyContinue }")


def backup(p):
    if p.exists():
        shutil.copy2(p, p.with_name(f"{p.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}"))


def items():
    """(tên, đạt chưa, hàm cài). Thứ tự quan trọng: tool trước, proxy trước khi trỏ Codex vào proxy."""
    out = []

    # --- runtime: hook ponytail chạy node, Claude Code cần Git Bash; bootstrap cài, ở đây chỉ kiểm ---
    def need(prog, hint):
        def fail():
            raise RuntimeError(f"thiếu {prog}: {hint}, rồi mở lại Claude/Codex")
        return fail
    sh_ok = shutil.which("sh") or (Path(r"C:\Program Files\Git\bin\sh.exe")).exists()
    out.append(("Node.js (hook ponytail)", bool(shutil.which("node") or Path(r"C:\Program Files\nodejs\node.exe").exists()
                                                  or (Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/nodejs/node.exe").exists()),
                need("node", "winget install OpenJS.NodeJS.LTS")))
    out.append(("Git Bash sh", bool(sh_ok), need("sh", "winget install Git.Git")))

    # --- uv tools ---
    for env, spec, py in UV_TOOLS:
        cmd = ["tool", "install", spec] + (["--python", py] if py else [])
        out.append((f"uv tool {spec}", (TOOLS / env / "uv-receipt.toml").exists(), lambda c=cmd: run(exe("uv"), *c)))

    # --- Claude Code ---
    claude_mcp = load(HOME / ".claude.json").get("mcpServers", {})
    for name, cmd in MCP.items():
        out.append((f"Claude MCP {name}", name in claude_mcp,
                    lambda n=name, c=cmd: run(exe("claude"), "mcp", "add", "--scope", "user", "--transport", "stdio", n, "--", *c)))
    installed = load(PLUGINS / "installed_plugins.json").get("plugins", {})
    for pid in PLUGIN_IDS:
        def do(pid=pid):
            mk = pid.split("@")[1]
            if mk not in load(PLUGINS / "known_marketplaces.json"):
                run(exe("claude"), "plugin", "marketplace", "add", MARKETS[mk])
            run(exe("claude"), "plugin", "install", pid, "--scope", "user")
        out.append((f"Claude plugin {pid}", pid in installed, do))
    out.append(("Claude bỏ plugin headroom (hook bật cửa sổ cmd)", HR_PLUGIN not in installed,
                lambda: run(exe("claude"), "plugin", "uninstall", HR_PLUGIN, "--scope", "user")))

    # --- Codex (GPT) ---
    has_codex = CODEX.exists() or codex_exe()

    def do_hr():
        if not (HOME / ".headroom" / "deploy" / "codex-local" / "manifest.json").exists():
            run(exe("headroom"), *HEADROOM_CODEX)
        stop_init_user()
        do_task()
        for _ in range(60):  # lần đầu proxy có thể mất hơn 1 phút để lên
            if proxy_ok():
                return
            time.sleep(2)
        raise RuntimeError(f"proxy không lên ở {PROXY}, xem ~/.headroom/deploy/codex-local/runner.log")
    hr_done = (HOME / ".headroom" / "deploy" / "codex-local" / "manifest.json").exists() and proxy_ok() and task_ok()
    if not has_codex:  # proxy không có Codex dùng thì chỉ tốn RAM
        out.append(("Codex: máy chưa có, bỏ qua proxy và phần Codex", True, None))
    else:
        out.append(("Headroom proxy cho Codex (codex-local, 8787, task ẩn)", hr_done, do_hr))

    if has_codex:
        cfg = CODEX / "config.toml"
        text = cfg.read_text(encoding="utf-8") if cfg.exists() else ""
        for name, cmd in CODEX_MCP.items():
            out.append((f"Codex MCP {name}", f"[mcp_servers.{name}]" in text,
                        lambda n=name, c=cmd: run(codex_exe(), "mcp", "add", n, "--", *c)))
        listing = ""
        try:
            listing = run(codex_exe(), "plugin", "list") if codex_exe() else ""
        except RuntimeError:
            pass
        for pid in PLUGIN_IDS:
            ok = any(l.split()[:1] == [pid] and "installed" in l and "not installed" not in l for l in listing.splitlines())

            def do_cp(pid=pid):
                mk = pid.split("@")[1]
                if f"[marketplaces.{mk}]" not in (cfg.read_text(encoding="utf-8") if cfg.exists() else ""):
                    run(codex_exe(), "plugin", "marketplace", "add", MARKETS[mk])
                run(codex_exe(), "plugin", "add", pid)
            out.append((f"Codex plugin {pid}", ok, do_cp))
        hr_on = any(l.split()[:1] == [HR_PLUGIN] and "installed" in l and "not installed" not in l
                    for l in listing.splitlines())
        out.append(("Codex bỏ plugin headroom (hook bật cửa sổ cmd)", not hr_on,
                    lambda: run(codex_exe(), "plugin", "remove", HR_PLUGIN)))

        hooks = CODEX / "hooks.json"

        def do_hooks():  # hook do "headroom init codex" ghi, cùng lỗi với plugin
            backup(hooks)
            d = load(hooks)
            for ev in list(d.get("hooks", {})):
                groups = []
                for g in d["hooks"][ev]:
                    g["hooks"] = [h for h in g.get("hooks", []) if "headroom" not in h.get("command", "")]
                    if g["hooks"]:
                        groups.append(g)
                if groups:
                    d["hooks"][ev] = groups
                else:
                    del d["hooks"][ev]
            hooks.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        out.append(("Codex hooks.json không gọi headroom", "headroom" not in (hooks.read_text(encoding="utf-8") if hooks.exists() else ""),
                    do_hooks))

        def do_route():
            if not proxy_ok():  # trỏ vào proxy chết thì Codex hỏng hẳn
                raise RuntimeError("proxy Headroom chưa chạy, không trỏ Codex vào")
            backup(cfg)
            t = cfg.read_text(encoding="utf-8") if cfg.exists() else ""
            top = [l for l in CODEX_TOP if f"\n{l.split(' =')[0]} =" not in "\n" + t]
            t = "\n".join(top + [t]) if top else t  # khóa gốc phải nằm trước bảng [..] đầu tiên
            if "[model_providers.headroom]" not in t:
                t += "\n" + CODEX_PROVIDER
            cfg.write_text(t, encoding="utf-8")
        routed = "[model_providers.headroom]" in text and all(f"\n{l}" in "\n" + text for l in CODEX_TOP)
        out.append(("Codex đi qua proxy Headroom", routed, do_route))

    # --- Gemini / Antigravity: chỉ Windows-MCP (Ponytail, Headroom chưa hỗ trợ) ---
    if GEMINI.exists():
        gs = GEMINI / "settings.json"

        def do_gem():
            backup(gs)
            d = load(gs)
            d.setdefault("mcpServers", {})["windows-mcp"] = {"command": MCP["windows-mcp"][0], "args": MCP["windows-mcp"][1:]}
            gs.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        out.append(("Gemini MCP windows-mcp", "windows-mcp" in load(gs).get("mcpServers", {}), do_gem))
    return out


def report(apply):
    pending = 0
    for name, ok, fn in items():
        st = "OK" if ok else "THIẾU"
        if not ok and apply:
            try:
                fn(); st = "XONG"
            except Skip as e:
                st = f"BỎ QUA ({e})"
            except Exception as e:
                st = f"LỖI: {e}"
        pending += not (st in ("OK", "XONG") or st.startswith("BỎ QUA"))
        print(f"{st:6} {name}")
    return pending


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode not in ("check", "apply"):
        raise SystemExit("dùng: setup.py check|apply")
    pending = report(mode == "apply")
    if mode == "apply":
        print("\n--- kiểm lại ---")
        pending = report(False)
    print(f"\nCòn {pending} mục chưa đạt." + (" Thoát hẳn rồi mở lại app Claude, Codex (để nhận PATH mới và nạp plugin, MCP)." if not pending else ""))
    sys.exit(1 if pending else 0)


if __name__ == "__main__":
    main()
