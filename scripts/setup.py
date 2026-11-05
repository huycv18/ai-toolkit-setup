"""Cài Windows-MCP, Ponytail, Headroom cho Claude Code trên máy Windows.

  check  so máy với danh sách, không sửa gì; exit 1 nếu còn thiếu
  apply  cài phần còn thiếu (idempotent)
"""
import json, shutil, subprocess, sys, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HOME = Path.home()
BIN = HOME / ".local" / "bin"
TOOLS = HOME / "AppData" / "Roaming" / "uv" / "tools"
PLUGINS = HOME / ".claude" / "plugins"

UV_TOOLS = [  # (tên env, spec, python); headroom cần đúng 3.13, đổi bản sẽ làm uv xóa env đang chạy
    ("windows-mcp", "windows-mcp", None),
    ("headroom-ai", "headroom-ai[proxy,code,mcp]", "3.13"),
]
PLUGIN_LIST = [  # (plugin@marketplace, nguồn marketplace)
    ("ponytail@ponytail", "https://github.com/dietrichgebert/ponytail.git"),
    ("headroom@headroom-marketplace", "https://github.com/headroomlabs-ai/headroom.git"),
]
# Claude desktop bỏ qua ANTHROPIC_BASE_URL nên proxy chỉ phục vụ Codex (DECISIONS 2026-11-05)
HEADROOM_CODEX = ["install", "apply", "--preset", "persistent-task", "--providers", "manual",
                  "--target", "codex", "--profile", "codex-local", "--port", "8787", "--mode", "cache",
                  "--no-telemetry", "--no-rate-limit", "--code-aware"]


CODEX = HOME / ".codex"
GEMINI = HOME / ".gemini"
_wmcp = str(BIN / "windows-mcp.exe").replace("'", "")
_hr = str(BIN / "headroom.exe").replace("'", "")
CODEX_BLOCKS = [  # (header nhận diện, khối TOML)
    ("[mcp_servers.windows-mcp]", f"[mcp_servers.windows-mcp]\ncommand = '{_wmcp}'\nargs = [\"serve\"]\n"),
    ("[marketplaces.ponytail]", '[marketplaces.ponytail]\nsource_type = "git"\nsource = "https://github.com/dietrichgebert/ponytail.git"\n'),
    ('[plugins."ponytail@ponytail"]', '[plugins."ponytail@ponytail"]\nenabled = true\n'),
    ("[marketplaces.headroom-marketplace]", '[marketplaces.headroom-marketplace]\nsource_type = "git"\nsource = "https://github.com/headroomlabs-ai/headroom.git"\n'),
    ('[plugins."headroom@headroom-marketplace"]', '[plugins."headroom@headroom-marketplace"]\nenabled = true\n'),
    ("[mcp_servers.headroom]", f"[mcp_servers.headroom]\ncommand = '{_hr}'\nargs = [\"mcp\", \"serve\"]\n"),
    ("[model_providers.headroom]", '[model_providers.headroom]\nname = "OpenAI"\nbase_url = "http://127.0.0.1:8787/v1"\nsupports_websockets = true\nrequires_openai_auth = true\n'),
]
CODEX_TOP = [  # Codex đi qua proxy Headroom
    ("model_provider", 'model_provider = "headroom"'),
    ("openai_base_url", 'openai_base_url = "http://127.0.0.1:8787/v1"'),
]


def load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def exe(name):
    p = BIN / f"{name}.exe"
    return str(p) if p.exists() else shutil.which(name)


def run(*cmd):
    print("  $", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip()[-500:])


def items():
    out = []
    for env, spec, py in UV_TOOLS:
        cmd = [exe("uv"), "tool", "install", spec] + (["--python", py] if py else [])
        out.append((f"uv tool {spec}", (TOOLS / env / "uv-receipt.toml").exists(), lambda c=cmd: run(*c)))

    mcp = load(HOME / ".claude.json").get("mcpServers", {})
    out.append(("MCP windows-mcp (user)", "windows-mcp" in mcp,
                lambda: run(exe("claude"), "mcp", "add", "--scope", "user", "--transport", "stdio",
                            "windows-mcp", "--", str(BIN / "windows-mcp.exe"), "serve")))

    installed = load(PLUGINS / "installed_plugins.json").get("plugins", {})
    for pid, src in PLUGIN_LIST:
        def do(pid=pid, src=src):
            if pid.split("@")[1] not in load(PLUGINS / "known_marketplaces.json"):
                run(exe("claude"), "plugin", "marketplace", "add", src)
            run(exe("claude"), "plugin", "install", pid, "--scope", "user")
        out.append((f"plugin {pid}", pid in installed, do))

    codex_cfg = CODEX / "config.toml"

    def do_hr():
        if not CODEX.exists():
            raise RuntimeError("máy chưa có Codex, cài Codex rồi chạy lại")
        run(exe("headroom"), *HEADROOM_CODEX)
    out.append(("Headroom proxy cho Codex (codex-local)",
                (HOME / ".headroom" / "deploy" / "codex-local" / "manifest.json").exists(), do_hr))

    # Codex (GPT): cùng 3 món, ghi thẳng config.toml
    if CODEX.exists():
        text = codex_cfg.read_text(encoding="utf-8") if codex_cfg.exists() else ""
        for header, block in CODEX_BLOCKS:
            out.append((f"Codex {header}", header in text, lambda b=block: codex_append(codex_cfg, b)))
        for key, line in CODEX_TOP:
            out.append((f"Codex {key}", f"\n{key} =" in "\n" + text, lambda l=line: codex_prepend(codex_cfg, l)))

    # Gemini / Antigravity: chỉ Windows-MCP (Ponytail, Headroom chưa hỗ trợ)
    if GEMINI.exists():
        gs = GEMINI / "settings.json"

        def do_gem():
            backup(gs)
            d = load(gs)
            d.setdefault("mcpServers", {})["windows-mcp"] = {"command": str(BIN / "windows-mcp.exe"), "args": ["serve"]}
            gs.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        out.append(("Gemini MCP windows-mcp", "windows-mcp" in load(gs).get("mcpServers", {}), do_gem))
    return out


def backup(p):
    if p.exists():
        shutil.copy2(p, p.with_name(f"{p.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}"))


def codex_append(cfg, block):
    backup(cfg)
    with open(cfg, "a", encoding="utf-8") as f:
        f.write("\n" + block)


def codex_prepend(cfg, line):
    # khóa cấp gốc phải nằm trước bảng [..] đầu tiên
    backup(cfg)
    old = cfg.read_text(encoding="utf-8") if cfg.exists() else ""
    cfg.write_text(line + "\n" + old, encoding="utf-8")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode not in ("check", "apply"):
        raise SystemExit("dùng: setup.py check|apply")
    pending = 0
    for name, ok, fn in items():
        st = "OK" if ok else "THIẾU"
        if not ok and mode == "apply":
            try:
                fn(); st = "XONG"
            except Exception as e:
                st = f"LỖI: {e}"
        pending += st not in ("OK", "XONG")
        print(f"{st:6} {name}")
    print(f"\nCòn {pending} mục chưa đạt." + (" Mở phiên Claude mới để nạp plugin và MCP." if mode == "apply" else ""))
    sys.exit(1 if pending else 0)


if __name__ == "__main__":
    main()
