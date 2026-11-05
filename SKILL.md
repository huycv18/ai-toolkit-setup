---
name: ai-toolkit-setup
description: Cài bộ công cụ chuẩn của Huy trên máy Windows mới cho Claude Code và các AI khác (Codex/GPT, Gemini/Antigravity) - Windows-MCP (điều khiển desktop), plugin Ponytail (giảm output), Headroom (plugin + proxy nén token cho Codex). Kiểm trước, chỉ cài phần thiếu. Dùng khi Huy nói "setup máy mới", "cài Windows-MCP, Ponytail, Headroom", hoặc gõ /ai-toolkit-setup.
---

# ai-toolkit-setup

Cài 3 món, chạy lại bao nhiêu lần cũng được:

| Món | Cài gì |
|---|---|
| Windows-MCP | `uv tool install windows-mcp` + `claude mcp add --scope user windows-mcp` |
| Ponytail | marketplace `dietrichgebert/ponytail` + plugin `ponytail@ponytail` |
| Headroom | `uv tool install headroom-ai[proxy,code,mcp]` (Python 3.13) + plugin `headroom@headroom-marketplace` + proxy `codex-local` cổng 8787 cho Codex |

Các AI khác trên máy, tự dò, có thì cài chung:

| AI | Có gì | Cách |
|---|---|---|
| Codex (GPT), có `~/.codex` | Đủ 3 món: MCP windows-mcp, plugin ponytail + headroom, MCP headroom, đi qua proxy 8787 (`model_provider = "headroom"`) | Ghi thêm khối vào `~/.codex/config.toml` (backup trước). Lần đầu mở Codex phải bấm tin cậy hook của plugin |
| Gemini / Antigravity, có `~/.gemini` | Chỉ Windows-MCP (Ponytail, Headroom chưa hỗ trợ) | Thêm vào `~/.gemini/settings.json` |

## Các bước

1. `powershell -ExecutionPolicy Bypass -File "<skill>/scripts/bootstrap.ps1" check` - tự cài uv và Claude Code CLI nếu thiếu, rồi báo mục THIẾU.
2. Chạy lại với `apply`.
3. Chạy `check` lần nữa, báo Huy bảng kết quả. Mục Headroom proxy LỖI vì chưa có Codex là bình thường: cài Codex rồi chạy lại.
4. Nhắc Huy mở phiên Claude mới để nạp plugin và MCP.

## Đã biết

- Không thêm `env.ANTHROPIC_BASE_URL` để đưa Claude qua Headroom: app desktop bỏ qua biến này (thử 05/11/2026).
- Không `uv tool install headroom-ai` với Python khác 3.13 khi proxy đang chạy: uv xóa env, proxy hỏng ở lần khởi động sau.
