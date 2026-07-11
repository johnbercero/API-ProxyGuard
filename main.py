import asyncio
import os
import secrets
import sqlite3

from fastapi import Depends, FastAPI, Form, HTTPException, status
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.security import HTTPBasic, HTTPBasicCredentials

app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}


security = HTTPBasic()
DB_FILE = "/app/data/proxy_vault.db"
LOG_FILE = "/app/data/proxy.log"

# 🔒 SECURITY DEFINITIONS: Change these to your preferred login details
ADMIN_USERNAME = os.getenv("PROXY_USER", "proxy_admin")
ADMIN_PASSWORD = os.getenv("PROXY_PASS", "proxy_password")


def init_db():
    os.makedirs("/app/data", exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name TEXT UNIQUE,
            fake_key TEXT UNIQUE,
            real_key TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Verifies the network user against the secure hardcoded credentials."""
    is_correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    is_correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/", response_class=HTMLResponse)
async def dashboard(username: str = Depends(authenticate_user)):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT tool_name, fake_key, real_key FROM api_keys")
    rows = cursor.fetchall()
    conn.close()

    table_rows = ""
    for tool, fake, real in rows:
        masked_real = real[:6] + "********" if len(real) > 6 else "********"
        table_rows += f"""
        <tr>
            <td class="tool-name">{tool}</td>
            <td class="fake-key">{fake}</td>
            <td class="real-key">{masked_real}</td>
            <td style="text-align:center;">
                <form action="/delete" method="POST" style="display:inline;">
                    <input type="hidden" name="tool_name" value="{tool}">
                    <button type="submit" class="btn btn-danger" style="padding:0.3rem 0.8rem; font-size:0.75rem;">✕</button>
                </form>
            </td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ProxyGuard Vault</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
                min-height: 100vh; color: #e0e0e0; padding: 2rem 1rem;
            }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .header {{
                background: rgba(255,255,255,0.04);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 16px; padding: 1.5rem 2rem;
                margin-bottom: 1.5rem;
                display: flex; justify-content: space-between; align-items: center;
            }}
            .header h1 {{ font-size: 1.4rem; font-weight: 700; color: #7dd3fc; }}
            .header h1 span {{ color: #f472b6; }}
            .header .meta {{ font-size: 0.8rem; color: #888; }}
            .header .meta strong {{ color: #b0b0b0; }}
            .badge {{ display: inline-block; padding: 0.15rem 0.6rem; border-radius: 20px; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }}
            .badge-green {{ background: rgba(52,211,153,0.15); color: #34d399; }}
            .card {{
                background: rgba(255,255,255,0.04);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 16px; padding: 1.5rem 2rem;
                margin-bottom: 1.5rem;
            }}
            .card-title {{ font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #888; margin-bottom: 1rem; }}
            .form-grid {{ display: grid; grid-template-columns: 1fr; gap: 1rem; }}
            @media (min-width: 640px) {{ .form-grid {{ grid-template-columns: 1fr 1fr 1fr; }} .form-actions {{ grid-column: 1 / -1; }} }}
            .form-group {{ display: flex; flex-direction: column; gap: 0.3rem; }}
            .form-group label {{ font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: #999; }}
            .form-group input {{
                background: rgba(0,0,0,0.3);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px; padding: 0.65rem 0.9rem;
                font-size: 0.85rem; color: #e0e0e0;
                outline: none; transition: border-color 0.2s;
            }}
            .form-group input:focus {{ border-color: #7dd3fc; }}
            .form-group input::placeholder {{ color: #555; }}
            .btn {{
                display: inline-flex; align-items: center; gap: 0.4rem;
                padding: 0.65rem 1.4rem; border-radius: 10px;
                font-size: 0.8rem; font-weight: 600; border: none; cursor: pointer;
                transition: all 0.2s; text-decoration: none;
            }}
            .btn-primary {{ background: linear-gradient(135deg, #7dd3fc, #38bdf8); color: #0f0f1a; }}
            .btn-primary:hover {{ transform: translateY(-1px); box-shadow: 0 4px 20px rgba(56,189,248,0.3); }}
            .btn-danger {{ background: rgba(239,68,68,0.12); color: #f87171; }}
            .btn-danger:hover {{ background: rgba(239,68,68,0.2); }}
            .table-wrap {{ overflow-x: auto; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
            th {{ text-align: left; padding: 0.75rem 0.5rem; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #777; border-bottom: 1px solid rgba(255,255,255,0.06); }}
            td {{ padding: 0.75rem 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.04); }}
            .tool-name {{ color: #7dd3fc; font-weight: 600; }}
            .fake-key {{ font-family: 'SF Mono', 'Fira Code', monospace; color: #a78bfa; font-size: 0.8rem; }}
            .real-key {{ font-family: 'SF Mono', 'Fira Code', monospace; color: #555; font-size: 0.8rem; }}
            .empty-msg {{ text-align: center; padding: 2rem 0; color: #666; font-size: 0.85rem; }}
            .terminal-box {{
                background: rgba(0,0,0,0.3);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px; padding: 1rem 1.5rem;
                font-family: 'SF Mono', 'Fira Code', monospace;
                font-size: 0.8rem; line-height: 1.8;
            }}
            .terminal-box .label {{ color: #7dd3fc; font-weight: 600; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.5rem; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
            .terminal-box code {{ color: #f472b6; }}
            .log-viewer {{
                background: rgba(0,0,0,0.4);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px;
                height: 240px;
                overflow-y: auto;
                padding: 0.75rem 1rem;
                font-family: 'SF Mono', 'Fira Code', monospace;
                font-size: 0.75rem;
                line-height: 1.7;
                white-space: nowrap;
            }}
            .log-viewer .line {{ color: #ccc; }}
            .log-viewer .line.dim {{ color: #555; }}
            .log-status {{
                font-size: 0.7rem;
                transition: color 0.3s;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1>🔐 Proxy<span>Guard</span> Vault</h1>
                    <div class="meta"><strong>{username}</strong> · <span class="badge badge-green">● Live</span></div>
                </div>
            </div>

            <div class="card">
                <div class="card-title">➕ Add Key Mapping</div>
                <form action="/save" method="POST" class="form-grid">
                    <div class="form-group">
                        <label>Tool / Vendor</label>
                        <input type="text" name="tool_name" placeholder="e.g. OpenAI" required>
                    </div>
                    <div class="form-group">
                        <label>Fake Key Name</label>
                        <input type="text" name="fake_key" placeholder="e.g. FAKE_OPENAI_KEY" required>
                    </div>
                    <div class="form-group">
                        <label>Real Private Key</label>
                        <input type="password" name="real_key" placeholder="sk-..." required>
                    </div>
                    <div class="form-actions" style="display: flex; justify-content: flex-end;">
                        <button type="submit" class="btn btn-primary">+ Add / Update</button>
                    </div>
                </form>
            </div>

            <div class="card">
                <div class="card-title">🗄️ Stored Mappings</div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Vendor</th>
                                <th>Fake Key</th>
                                <th>Real Key</th>
                                <th style="text-align:center;">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows if table_rows else '<tr><td colspan="4" class="empty-msg">No keys yet. Add your first mapping above.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="terminal-box">
                <div class="label">💻 Terminal Setup</div>
                <code>export http_proxy=http://127.0.0.1:8080</code><br>
                <code>export https_proxy=http://127.0.0.1:8080</code>
            </div>

            <div class="card">
                <div class="card-title">🔒 CA Certificate</div>
                <p style="font-size:0.8rem; color:#999; margin-bottom:0.8rem;">
                    Install the proxy CA certificate to avoid using <code>-k</code> with curl.
                    Download and double-click the file to install on your system.
                </p>
                <a href="/ca-cert" class="btn btn-primary" style="font-size:0.75rem; padding:0.5rem 1rem;">
                    ⬇️ Download CA Certificate
                </a>
            </div>

            <div class="card">
                <div class="card-title" style="display:flex; justify-content:space-between; align-items:center;">
                    <span>📡 Live Proxy Logs</span>
                    <span id="log-status" class="log-status" style="color:#555;">● waiting...</span>
                </div>
                <div id="log-viewer" class="log-viewer">
                    <div class="line dim">Waiting for proxy traffic...</div>
                </div>
            </div>
        </div>
        <script>
            fetch('/logs')
                .then(r => r.json())
                .then(data => {{
                    const viewer = document.getElementById('log-viewer');
                    viewer.innerHTML = '';
                    if (data.logs.length === 0) {{
                        const div = document.createElement('div');
                        div.className = 'line dim';
                        div.textContent = 'No recent logs. Make a request through the proxy.';
                        viewer.appendChild(div);
                    }} else {{
                        data.logs.forEach(line => {{
                            const div = document.createElement('div');
                            div.className = 'line';
                            div.textContent = line;
                            viewer.appendChild(div);
                        }});
                    }}
                    viewer.scrollTop = viewer.scrollHeight;
                }})
                .catch(() => {{
                    const viewer = document.getElementById('log-viewer');
                    viewer.innerHTML = '<div class="line dim">Could not load logs.</div>';
                }});
            if (window.EventSource) {{
                const source = new EventSource('/logs/stream');
                source.onmessage = function(e) {{
                    const viewer = document.getElementById('log-viewer');
                    const dim = viewer.querySelector('.dim');
                    if (dim) dim.remove();
                    const div = document.createElement('div');
                    div.className = 'line';
                    div.textContent = e.data;
                    viewer.appendChild(div);
                    viewer.scrollTop = viewer.scrollHeight;
                    const status = document.getElementById('log-status');
                    status.textContent = '● live';
                    status.style.color = '#34d399';
                }};
                source.onerror = function() {{
                    const status = document.getElementById('log-status');
                    status.textContent = '● disconnected';
                    status.style.color = '#f87171';
                }};
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/logs")
async def get_logs(username: str = Depends(authenticate_user), lines: int = 50):
    if not os.path.exists(LOG_FILE):
        return {"logs": []}
    with open(LOG_FILE, "r") as f:
        all_lines = f.readlines()
    last_lines = all_lines[-lines:]
    return {"logs": [line.strip() for line in last_lines]}


@app.get("/logs/stream")
async def stream_logs(username: str = Depends(authenticate_user)):
    async def event_generator():
        while not os.path.exists(LOG_FILE):
            await asyncio.sleep(0.5)
        with open(LOG_FILE, "r") as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    yield f"data: {line.strip()}\n\n"
                else:
                    await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


CA_CERT_PATH = os.path.expanduser("~/.mitmproxy/mitmproxy-ca-cert.pem")


@app.get("/ca-cert")
async def download_ca_cert(username: str = Depends(authenticate_user)):
    if not os.path.exists(CA_CERT_PATH):
        return HTMLResponse(
            "<h3>CA certificate not yet generated.</h3>"
            "<p>Make a request through the proxy first to trigger certificate generation, then reload this page.</p>",
            status_code=404,
        )
    return FileResponse(
        CA_CERT_PATH,
        media_type="application/x-x509-ca-cert",
        filename="mitmproxy-ca-cert.pem",
    )


@app.post("/save")
async def save_key(
    tool_name: str = Form(...),
    fake_key: str = Form(...),
    real_key: str = Form(...),
    username: str = Depends(authenticate_user),
):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO api_keys (tool_name, fake_key, real_key)
        VALUES (?, ?, ?)
    """,
        (tool_name.strip(), fake_key.strip(), real_key.strip()),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)


@app.post("/delete")
async def delete_key(
    tool_name: str = Form(...), username: str = Depends(authenticate_user)
):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM api_keys WHERE tool_name = ?", (tool_name,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)
