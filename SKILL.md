---
name: ai-toolkit-setup
description: Cài bộ công cụ chuẩn của Huy trên máy Windows mới cho Claude Code và các AI khác (Codex/GPT, Gemini/Antigravity) - Windows-MCP (điều khiển desktop), plugin Ponytail (giảm output), Headroom (MCP + proxy nén token cho Codex, chạy ẩn). Một lệnh, không hỏi gì, chỉ cài phần thiếu, tự kiểm lại. Dùng khi Huy nói "setup máy mới", "cài Windows-MCP, Ponytail, Headroom", hoặc gõ /ai-toolkit-setup.
---

# ai-toolkit-setup

Một lệnh, chạy lại bao nhiêu lần cũng được (chỉ cài phần thiếu, cài xong tự kiểm lại):

`powershell -ExecutionPolicy Bypass -File "<skill>/scripts/bootstrap.ps1" apply`

Bootstrap tự cài Git, Node.js LTS (hook ponytail cần; winget hỏng thì tải zip vào thư mục người dùng, không cần admin), uv, Claude Code CLI nếu thiếu, bật `git core.longpaths`, rồi chạy `setup.py` bằng Python 3.13 qua uv. Dùng `check` thay `apply` để chỉ xem, không sửa.

| AI | Windows-MCP | Ponytail | Headroom |
|---|---|---|---|
| Claude Code | `claude mcp add --scope user` | `claude plugin install` | không, gỡ plugin headroom nếu có (Claude không đi qua proxy được) |
| Codex (GPT), tự dò | `codex mcp add` | `codex plugin add` | MCP + proxy `codex-local` cổng 8787 chạy bằng task ẩn `ai-toolkit-headroom-codex`; gỡ plugin headroom và hook headroom trong `~/.codex/hooks.json`; `model_provider = "headroom"` |
| Gemini / Antigravity, có `~/.gemini` | `settings.json` | chưa hỗ trợ | chưa hỗ trợ |

Không có Codex thì bỏ qua proxy và phần Codex (không tính là lỗi). Cài Codex sau thì chạy lại `apply`.

## Báo Huy

Bảng kết quả của lượt "kiểm lại" cuối, rồi nhắc việc chỉ người làm được:
- Đăng nhập Claude, Codex (không tự động được).
- Mở phiên mới của Claude, Codex để nạp plugin và MCP. Lần đầu Codex hỏi tin cậy hook của plugin ponytail: bấm tin cậy.

## Phát hành

Nguồn gốc ở studio repo `skills/ai-toolkit-setup`; repo public `huycv18/ai-toolkit-setup` là bản tách ra cho lệnh một dòng. Sửa xong thì đẩy (Huy cho tự push repo này, 05/11/2026):
`git subtree split -P skills/ai-toolkit-setup -b toolkit-pub && git push toolkit toolkit-pub:main`

## Đã biết

- Installer bên thứ ba (uv, Claude) có `exit`: chạy qua `iex` trực tiếp sẽ đóng cửa sổ của Huy (lỗi thật 05/11/2026). Bootstrap chạy chúng ở process con, bọc toàn bộ trong script block, ghi log `%USERPROFILE%\ai-toolkit-setup.log`, dừng chờ Enter ở cuối.

- Đã chạy thử trên home trắng giả lập 05/11/2026: đạt hết, trừ plugin Headroom của Codex do đường dẫn home giả quá dài; với đường dẫn như máy thật thì cài được.
- Codex chỉ được trỏ vào proxy khi proxy đã trả `/health` ready; trỏ vào proxy chết thì Codex hỏng hẳn.
- Không thêm `env.ANTHROPIC_BASE_URL` để đưa Claude qua Headroom: app desktop bỏ qua biến này (thử 05/11/2026).
- Không `uv tool install headroom-ai` với Python khác 3.13 khi proxy đang chạy: uv xóa env, proxy hỏng ở lần khởi động sau.
