import os
import secrets
import sqlite3

from fastapi import Depends, FastAPI, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

app = FastAPI()
security = HTTPBasic()
DB_FILE = "/app/data/proxy_vault.db"

# 🔒 SECURITY DEFINITIONS: Change these to your preferred login details
ADMIN_USERNAME = os.getenv("PROXY_USER", "jrb-admin")
ADMIN_PASSWORD = os.getenv("PROXY_PASS", "orecreB!")


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
        <tr class="border-b border-gray-700">
            <td class="p-3 text-emerald-400 font-medium">{tool}</td>
            <td class="p-3 font-mono text-gray-300">{fake}</td>
            <td class="p-3 font-mono text-gray-500">{masked_real}</td>
            <td class="p-3">
                <form action="/delete" method="POST" class="inline">
                    <input type="hidden" name="tool_name" value="{tool}">
                    <button type="submit" class="text-red-400 hover:text-red-600 text-sm font-semibold">Delete</button>
                </form>
            </td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://tailwindcss.com"></script>
        <title>Privacy Guard Studio</title>
    </head>
    <body class="bg-gray-900 text-white font-sans p-8">
        <div class="max-w-3xl mx-auto bg-gray-800 p-6 rounded-lg shadow-2xl border border-gray-700">
            <div class="flex justify-between items-center mb-6">
                <div>
                    <h1 class="text-2xl font-bold text-emerald-400">🛡️ Privacy Proxy Vault</h1>
                    <p class="text-sm text-gray-400">User: <span class="text-gray-300 font-semibold">{username}</span> | Status: <span class="text-emerald-500 font-bold">● SECURE</span></p>
                </div>
            </div>

            <!-- Key Input Form -->
            <form action="/save" method="POST" class="bg-gray-900 p-4 rounded-lg mb-8 grid grid-cols-1 md:grid-cols-3 gap-4 border border-gray-700">
                <div>
                    <label class="block text-xs uppercase text-gray-400 mb-1 font-bold">Tool/Vendor Name</label>
                    <input type="text" name="tool_name" placeholder="e.g. Tavily" class="w-full bg-gray-800 p-2 rounded border border-gray-700 text-sm text-white focus:outline-none focus:border-emerald-500" required>
                </div>
                <div>
                    <label class="block text-xs uppercase text-gray-400 mb-1 font-bold">Fake Token Name</label>
                    <input type="text" name="fake_key" placeholder="e.g. FAKE_TAVILY_KEY" class="w-full bg-gray-800 p-2 rounded border border-gray-700 text-sm text-white focus:outline-none focus:border-emerald-500" required>
                </div>
                <div>
                    <label class="block text-xs uppercase text-gray-400 mb-1 font-bold">Real Private Key</label>
                    <input type="password" name="real_key" placeholder="Paste actual secret" class="w-full bg-gray-800 p-2 rounded border border-gray-700 text-sm text-white focus:outline-none focus:border-emerald-500" required>
                </div>
                <div class="md:col-span-3 flex justify-end">
                    <button type="submit" class="bg-emerald-500 hover:bg-emerald-600 px-4 py-2 rounded text-sm font-semibold transition shadow-md">Add/Update Key</button>
                </div>
            </form>

            <!-- Storage Matrix -->
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="border-b border-gray-700 text-gray-400 text-xs uppercase">
                            <th class="p-3">Vendor</th>
                            <th class="p-3">Fake Placeholder</th>
                            <th class="p-3">Real Key Status</th>
                            <th class="p-3">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows if table_rows else '<tr><td colspan="4" class="p-4 text-center text-gray-500 text-sm">No keys stored yet. Register your first mapping above!</td></tr>'}
                    </tbody>
                </table>
            </div>

            <div class="mt-8 bg-gray-900 p-4 rounded text-xs font-mono text-gray-400 border border-gray-800 space-y-1">
                <p class="text-emerald-400 font-bold mb-1">💡 Terminal Hook Activation Commands:</p>
                <p>export http_proxy=http://127.0.0.1:8080</p>
                <p>export https_proxy=http://127.0.0.1:8080</p>
                <p>export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


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
