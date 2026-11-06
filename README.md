# ai-toolkit-setup

Cài một lệnh trên Windows 10/11 cho Claude Code, Codex (GPT), Gemini / Antigravity:

- **Windows-MCP** - AI điều khiển desktop Windows
- **Ponytail** - plugin giảm output, code tối giản
- **Headroom** - MCP và proxy nén token cho Codex, chạy ẩn bằng task `ai-toolkit-headroom-codex` (không cài plugin headroom: hook của nó bật cửa sổ cmd)

## Cài

Mở PowerShell, dán:

```powershell
irm https://raw.githubusercontent.com/huycv18/ai-toolkit-setup/main/scripts/bootstrap.ps1 | iex
```

Script tự cài Git, Node.js LTS (winget, không được thì bản zip vào `%LOCALAPPDATA%\Programs\nodejs`, không cần admin), uv, Claude Code CLI nếu thiếu; chỉ cài phần còn thiếu; cài xong tự kiểm lại. Chạy lại bao nhiêu lần cũng được.

Chỉ kiểm, không sửa: tải repo về rồi chạy `powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1 check`.

## Sau khi cài

1. Đăng nhập Claude và Codex.
2. Mở phiên mới để nạp plugin và MCP. Lần đầu Codex hỏi tin cậy hook của ponytail: bấm tin cậy.

| AI | Windows-MCP | Ponytail | Headroom |
|---|---|---|---|
| Claude Code | MCP user | plugin | không (Claude không đi qua proxy được) |
| Codex | MCP | plugin | MCP + proxy 127.0.0.1:8787 (task ẩn) |
| Gemini / Antigravity | MCP | - | - |
