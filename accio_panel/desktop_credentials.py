from __future__ import annotations

import json
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from .models import normalize_timestamp


class DesktopCredentialImportError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DesktopCredentials:
    access_token: str
    refresh_token: str
    expires_at: int | None
    cookie: str | None
    utdid: str
    user_id: str = ""
    user_name: str = ""

    def to_account_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "accessToken": self.access_token,
            "refreshToken": self.refresh_token,
            "expiresAt": self.expires_at,
            "cookie": self.cookie,
            "utdid": self.utdid,
        }
        if self.user_id:
            payload["id"] = f"desktop-{self.user_id}"
        if self.user_name:
            payload["name"] = f"桌面端-{self.user_name}"
        return payload


def load_accio_desktop_credentials(timeout_seconds: float = 8.0) -> DesktopCredentials:
    app_binary = _find_accio_app_binary()
    credentials_path = Path.home() / "Library/Application Support/Accio/credentials.enc"
    utdid_path = Path.home() / ".accio" / "utdid"

    if not credentials_path.is_file():
        raise DesktopCredentialImportError(
            f"未找到官方客户端凭据文件：{credentials_path}"
        )
    if not utdid_path.is_file():
        raise DesktopCredentialImportError(f"未找到官方客户端 UTDID 文件：{utdid_path}")

    port = _pick_free_port()
    log_file = tempfile.TemporaryFile(mode="w+b")
    process = subprocess.Popen(
        [str(app_binary), f"--inspect={port}"],
        stdout=log_file,
        stderr=log_file,
        text=False,
    )

    try:
        ws_url = _wait_for_inspector_ws_url(port, timeout_seconds)
        payload = _read_credentials_via_inspector(
            ws_url=ws_url,
            credentials_path=credentials_path,
            utdid_path=utdid_path,
            timeout_seconds=timeout_seconds,
        )
    except Exception as exc:
        log_file.seek(0)
        raw_logs = log_file.read().decode("utf-8", errors="replace").strip()
        if isinstance(exc, DesktopCredentialImportError):
            message = str(exc)
        else:
            message = f"读取官方客户端凭据失败：{exc}"
        if raw_logs:
            message = f"{message}\n{raw_logs[-1200:]}"
        raise DesktopCredentialImportError(message) from exc
    finally:
        _terminate_process(process)
        log_file.close()

    access_token = str(payload.get("accessToken") or "").strip()
    refresh_token = str(payload.get("refreshToken") or "").strip()
    utdid = str(payload.get("utdid") or "").strip()

    if not access_token or not refresh_token:
        raise DesktopCredentialImportError("官方客户端凭据缺少 accessToken 或 refreshToken")
    if not utdid:
        raise DesktopCredentialImportError("官方客户端凭据缺少 UTDID")

    return DesktopCredentials(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=normalize_timestamp(payload.get("expiresAt")),
        cookie=str(payload.get("cookie") or "").strip() or None,
        utdid=utdid,
        user_id=str(payload.get("userId") or "").strip(),
        user_name=str(payload.get("userName") or "").strip(),
    )


def _find_accio_app_binary() -> Path:
    candidates = [
        Path("/Applications/Accio.app/Contents/MacOS/Accio"),
        Path.home() / "Applications/Accio.app/Contents/MacOS/Accio",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise DesktopCredentialImportError("未找到官方 Accio 桌面端，请先安装官方客户端。")


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_inspector_ws_url(port: int, timeout_seconds: float) -> str:
    deadline = time.time() + timeout_seconds
    last_error: str | None = None
    while time.time() < deadline:
        try:
            with urlopen(
                f"http://127.0.0.1:{port}/json/list",
                timeout=0.5,
            ) as response:
                items = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError, URLError) as exc:
            last_error = str(exc)
            time.sleep(0.2)
            continue

        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                ws_url = str(item.get("webSocketDebuggerUrl") or "").strip()
                if ws_url:
                    return ws_url
        time.sleep(0.2)

    detail = f"（最后错误：{last_error}）" if last_error else ""
    raise DesktopCredentialImportError(f"等待官方客户端调试端口超时{detail}")


def _read_credentials_via_inspector(
    *,
    ws_url: str,
    credentials_path: Path,
    utdid_path: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    node_script = r"""
const wsUrl = process.argv[1];
const credentialsPath = process.argv[2];
const utdidPath = process.argv[3];

const expr = `(async () => {
  const Module = process.getBuiltinModule("module");
  const fs = process.getBuiltinModule("fs");
  const req = Module.createRequire(process.cwd() + "/inspector.js");
  const { app, safeStorage } = req("electron");
  if (!app.isReady()) {
    await new Promise((resolve) => app.once("ready", resolve));
  }
  const raw = fs.readFileSync(${JSON.stringify(String(credentialsPath))});
  const text = safeStorage.decryptString(raw);
  const data = JSON.parse(text);
  const utdid = fs.readFileSync(${JSON.stringify(String(utdidPath))}, "utf8").trim();
  return JSON.stringify({
    accessToken: String(data.accessToken || ""),
    refreshToken: String(data.refreshToken || ""),
    expiresAt: data.expiresAt,
    cookie: typeof data.cookie === "string" ? data.cookie : "",
    utdid,
    userId: data.user && data.user.id ? String(data.user.id) : "",
    userName:
      data.user &&
      (data.user.name || data.user.nickName || data.user.loginId)
        ? String(data.user.name || data.user.nickName || data.user.loginId)
        : "",
  });
})()`;

const ws = new WebSocket(wsUrl);

ws.onopen = () => {
  ws.send(
    JSON.stringify({
      id: 1,
      method: "Runtime.evaluate",
      params: {
        expression: expr,
        returnByValue: true,
        awaitPromise: true,
      },
    }),
  );
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data.toString());
  if (message.id !== 1) {
    return;
  }
  const details = message.result && message.result.exceptionDetails;
  if (details) {
    const error = message.result.result || {};
    console.error(error.description || details.text || "Runtime.evaluate failed");
    process.exit(1);
    return;
  }
  const value = message.result && message.result.result && message.result.result.value;
  if (typeof value !== "string" || !value) {
    console.error("Desktop credentials result missing");
    process.exit(1);
    return;
  }
  process.stdout.write(`${value}\n`);
  ws.close();
};

ws.onerror = (error) => {
  console.error(String(error && error.message ? error.message : error));
  process.exit(1);
};
"""
    completed = subprocess.run(
        ["node", "-e", node_script, ws_url, str(credentials_path), str(utdid_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=max(timeout_seconds, 3.0),
    )
    if completed.returncode != 0:
        raise DesktopCredentialImportError(
            completed.stderr.strip() or completed.stdout.strip() or "Node helper failed"
        )
    try:
        payload = json.loads(completed.stdout.strip())
    except json.JSONDecodeError as exc:
        raise DesktopCredentialImportError("官方客户端返回的凭据不是合法 JSON") from exc
    if not isinstance(payload, dict):
        raise DesktopCredentialImportError("官方客户端返回的凭据格式无效")
    return payload


def _terminate_process(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)
