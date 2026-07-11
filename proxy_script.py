import sqlite3

from mitmproxy import http

DB_FILE = "/app/data/proxy_vault.db"


def get_live_mappings():
    """Queries the shared SQLite database file for updated key lists."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT fake_key, real_key FROM api_keys")
        rows = cursor.fetchall()
        conn.close()
        return {fake.encode(): real.encode() for fake, real in rows}
    except Exception:
        return {}


def request(flow: http.HTTPFlow) -> None:
    api_map = get_live_mappings()

    for fake_key, real_key in api_map.items():
        if not real_key:
            continue

        api_name = fake_key.decode().replace("FAKE_", "").replace("_KEY", "")
        swapped = False

        # 1. Body Interception (POST / JSON Payloads)
        if flow.request.content and fake_key in flow.request.content:
            flow.request.content = flow.request.content.replace(fake_key, real_key)
            swapped = True

        # 2. Header Interception (Bearer Tokens, X-API-Keys)
        for header_name, header_value in flow.request.headers.items():
            fake_str = fake_key.decode()
            if fake_str in header_value:
                flow.request.headers[header_name] = header_value.replace(
                    fake_str, real_key.decode()
                )
                swapped = True

        # 3. URL Query Parameters (GET Requests)
        if fake_key.decode() in flow.request.url:
            flow.request.url = flow.request.url.replace(
                fake_key.decode(), real_key.decode()
            )
            swapped = True

        # Log visibility tracking inside Dokploy containers
        if swapped:
            print(
                f"[API ProxyGuard] Swapped placeholder for tool: {api_name}", flush=True
            )
