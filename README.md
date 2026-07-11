# 🔐 ProxyGuard Vault

A self-hosted **MITM proxy** that intercepts HTTP/HTTPS requests and automatically swaps fake placeholder API keys with your real keys — keeping secrets out of your source code.

```
FAKE_OPENAI_KEY  ──→  proxyguard  ──→  sk-real-key-abc123...
FAKE_TAVILY_KEY  ──→  proxyguard  ──→  tvly-real-key-xyz789...
```

---

## 📋 Table of Contents

- [How It Works](#how-it-works)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
  - [1. Access the Dashboard](#1-access-the-dashboard)
  - [2. Add an API Key Mapping](#2-add-an-api-key-mapping)
  - [3. Use the Proxy](#3-use-the-proxy)
  - [4. Install the CA Certificate (Optional)](#4-install-the-ca-certificate-optional)
- [Live Log Monitor](#live-log-monitor)
- [Dashboard Reference](#dashboard-reference)
- [API Endpoints](#api-endpoints)
- [Environment Variables](#environment-variables)
- [How the Key Swap Works](#how-the-key-swap-works)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)

---

## 🧠 How It Works

```
┌─────────────────────────────────────────────────────┐
│                  ProxyGuard Container                │
│                                                     │
│  ┌──────────────────┐      ┌────────────────────┐   │
│  │  FastAPI Dashboard │      │  mitmproxy Engine   │   │
│  │  (Port 8000)       │      │  (Port 8080)        │   │
│  │                    │      │                     │   │
│  │  - Manage mappings │      │  - Intercepts HTTP  │   │
│  │  - View live logs  │      │  - Swaps keys in:   │   │
│  │  - Download CA cert│      │    · Headers        │   │
│  └────────┬───────────┘      │    · Body (JSON)    │   │
│           │                  │    · URL Query Params│   │
│           │                  └────────┬────────────┘   │
│           └──────────┬───────────────┘                │
│                      │                                │
│              ┌───────▼────────┐                       │
│              │   SQLite DB     │                       │
│              │proxy_vault.db   │                       │
│              │  (persistent)   │                       │
│              └────────────────┘                       │
└─────────────────────────────────────────────────────┘
         │
         │  Your apps route traffic through the proxy
         ▼
┌─────────────────────┐
│  Your Local Machine  │
│                     │
│  curl / Python /     │
│  Node.js / etc.     │
│                     │
│  http_proxy=         │
│    =127.0.0.1:8080  │
└─────────────────────┘
```

**Flow for a typical request:**

1. Your app sends a request with a **fake key** (e.g., `FAKE_OPENAI_KEY`)
2. The request goes through the proxy at `127.0.0.1:8080`
3. mitmproxy inspects the request (headers, body, URL)
4. ProxyGuard looks up the mapping in the SQLite database
5. The fake key is replaced with your **real key**
6. The modified request is forwarded to the real API
7. The response is sent back to your app — completely transparent

---

## ✨ Features

| Feature | Description |
|---|---|
| **🔐 Key Swapping** | Automatically replaces fake keys in headers, JSON body, and URL query params |
| **🌐 HTTPS Support** | Full MITM proxy with SSL interception (self-signed CA) |
| **🖥️ Web Dashboard** | Clean UI to add, view, and delete key mappings |
| **📡 Live Log Monitor** | Real-time SSE stream showing every request and swap |
| **🔒 Basic Auth** | Password-protected dashboard with secure defaults |
| **🐳 Dockerized** | Single `docker compose up` to run everything |
| **💾 Persistent Storage** | SQLite database + CA cert survive container restarts |
| **🔄 Live Reload** | Proxy reads mappings from DB on every request — no restart needed |

---

## 📦 Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+)
- A Debian-based Linux distribution (e.g., Debian 13, Ubuntu) or Windows with Docker Desktop

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/johnbercero/API-ProxyGuard.git
cd API-ProxyGuard
```

### 2. Start the Container

```bash
docker compose up -d --build
```

This builds the Docker image and starts the service in the background.

### 3. Verify It's Running

```bash
docker ps | grep proxyguard
```

You should see output like:

```
abc123def456   api-proxyguard-apiguard   "/app/entrypoint.sh"   Up 2 minutes   0.0.0.0:8000->8000/tcp, 127.0.0.1:8080->8080/tcp
```

### 4. Open the Dashboard

Visit [**http://localhost:8000**](http://localhost:8000) in your browser.

Default login:
- **Username**: `proxy_admin`
- **Password**: `proxy_password`

---

## 🎯 Usage Guide

### 1. Access the Dashboard

Open `http://localhost:8000` and log in. You'll see:

```
┌──────────────────────────────────────┐
│  🔐 ProxyGuard Vault                  │
│  proxy_admin · ● Live                   │
├──────────────────────────────────────┤
│  ➕ Add Key Mapping                   │
│  ┌──────────┬────────────┬──────────┐ │
│  │ Tool     │ Fake Key   │ Real Key │ │
│  │ Name     │ Name       │ (hidden) │ │
│  └──────────┴────────────┴──────────┘ │
│  [               + Add / Update     ] │
├──────────────────────────────────────┤
│  🗄️ Stored Mappings                   │
│  ┌────────┬────────────┬────────┬────┐│
│  │ Vendor │ Fake Key   │Real Key│ Act││
│  ├────────┼────────────┼────────┼────┤│
│  │ Tavily │FAKE_TAVILY │ tvly...│  ✕ ││
│  └────────┴────────────┴────────┴────┘│
├──────────────────────────────────────┤
│  🔒 CA Certificate                    │
│  [ ⬇️ Download CA Certificate ]       │
├──────────────────────────────────────┤
│  📡 Live Proxy Logs                   │
│  ┌──────────────────────────────────┐ │
│  │ 2026-07-11 | POST | api.tavily... │ │
│  │ ... | Swapped TAVILY key          │ │
│  └──────────────────────────────────┘ │
└──────────────────────────────────────┘
```

### 2. Add an API Key Mapping

In the **"Add Key Mapping"** form:

| Field | Example Value | Description |
|---|---|---|
| **Tool / Vendor** | `Tavily` | A friendly name for the API |
| **Fake Key Name** | `FAKE_TAVILY_KEY` | The placeholder key you'll use in your code |
| **Real Private Key** | `tvly-dev-abc...` | Your actual API key (stored encrypted in the DB) |

Click **"+ Add / Update"** to save.

> **💡 Tip**: Use descriptive fake key names that match your vendor:
> - `FAKE_OPENAI_KEY` → sk-...
> - `FAKE_TAVILY_KEY` → tvly-...
> - `FAKE_SERPAPI_KEY` → serp-...

### 3. Use the Proxy

Route your terminal traffic through the proxy:

```bash
export http_proxy=http://127.0.0.1:8080
export https_proxy=http://127.0.0.1:8080
```

Or use the `-x` flag with curl:

```bash
curl -x http://127.0.0.1:8080 \
  -H "Authorization: Bearer FAKE_TAVILY_KEY" \
  "https://api.tavily.com/extract" \
  -d '{"urls": ["https://example.com"]}'
```

The proxy will automatically:
1. ✅ Detect `FAKE_TAVILY_KEY` in the header
2. 🔄 Look up the real key from the database
3. ✏️ Replace it before forwarding to Tavily
4. ✅ Return the response to you

### 4. Install the CA Certificate (Optional)

Without installing the CA certificate, you need `-k` (or `--insecure`) with every curl command. Install it once to remove this requirement.

#### From the Dashboard (easiest)

1. Go to [**http://localhost:8000**](http://localhost:8000)
2. Click **"⬇️ Download CA Certificate"**
3. Save the file

#### From the mounted volume (no browser needed)

The cert is also available at `./mitmproxy-ca/mitmproxy-ca-cert.pem` in your project directory.

#### Install on Debian / Ubuntu / Linux Mint

```bash
# Copy the certificate to the system trust store
sudo cp ./mitmproxy-ca/mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt

# Update the system certificate store
sudo update-ca-certificates
```

#### Install on Windows

1. Double-click `mitmproxy-ca-cert.pem`
2. Select **"Install Certificate"**
3. Choose **"Local Machine" → "Trusted Root Certification Authorities"**
4. Click **Finish**

#### Verify it works

```bash
# Without -k — should succeed if cert is installed
curl -x http://127.0.0.1:8080 "https://example.com"
```

---

## 📡 Live Log Monitor

The dashboard includes a **real-time log viewer** that streams proxy activity as it happens.

**What you'll see:**

```
2026-07-11 02:15:30 | POST | api.openai.com/v1/chat | Swapped OPENAI key
2026-07-11 02:15:31 | GET  | api.tavily.com/search  | Swapped TAVILY key
```

| Column | Meaning |
|---|---|
| **Timestamp** | When the request was intercepted |
| **Method** | HTTP method (GET, POST, PUT, etc.) |
| **Host + Path** | The destination API endpoint (query params removed for security) |
| **Action** | What was swapped (e.g., `Swapped OPENAI key`) |

The log viewer uses **Server-Sent Events (SSE)** for real-time updates — no page refresh needed.

---

## 🖥️ Dashboard Reference

### Cards / Sections

| Section | Description |
|---|---|
| **Header** | Shows logged-in user and live status indicator |
| **Add Key Mapping** | Form to register a new fake-key → real-key mapping |
| **Stored Mappings** | Table of all registered mappings with delete action |
| **CA Certificate** | Download the proxy's CA cert for trusted HTTPS |
| **Live Proxy Logs** | Real-time stream of intercepted requests |

### Buttons

| Button | Action |
|---|---|
| **+ Add / Update** | Saves a new mapping or updates an existing one (by tool name) |
| **✕ (Delete)** | Removes a mapping from the database |
| **⬇️ Download CA Certificate** | Downloads the mitmproxy CA cert for system-wide trust |

---

## 🔌 API Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/` | GET | ✅ Basic Auth | Dashboard HTML page |
| `/health` | GET | ❌ None | Health check (returns `{"status": "ok"}`) |
| `/save` | POST | ✅ Basic Auth | Add/update a key mapping |
| `/delete` | POST | ✅ Basic Auth | Delete a key mapping |
| `/logs` | GET | ✅ Basic Auth | Returns last 50 log lines |
| `/logs/stream` | GET | ✅ Basic Auth | SSE stream for real-time logs |
| `/ca-cert` | GET | ✅ Basic Auth | Downloads the mitmproxy CA certificate |

---

## 🌍 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PROXY_USER` | `proxy_admin` | Dashboard admin username |
| `PROXY_PASS` | `proxy_password` | Dashboard admin password |

Set them in your `docker-compose.yml` or in a `.env` file:

```yaml
services:
  api-proxyguard:
    environment:
      - PROXY_USER=myuser
      - PROXY_PASS=mypassword
```

---

## ⚙️ How the Key Swap Works

The proxy script (`proxy_script.py`) intercepts every HTTP/HTTPS request and checks **three locations** for fake keys:

### 1. Request Headers

```python
for header_name, header_value in flow.request.headers.items():
    if fake_str in header_value:
        flow.request.headers[header_name] = header_value.replace(
            fake_str, real_key
        )
```

Matches in: `Authorization: Bearer FAKE_OPENAI_KEY`, `X-API-Key: FAKE_OPENAI_KEY`, custom headers, etc.

### 2. Request Body (JSON / Form data)

```python
if flow.request.content and fake_key in flow.request.content:
    flow.request.content = flow.request.content.replace(fake_key, real_key)
```

Matches in: JSON payloads like `{"api_key": "FAKE_OPENAI_KEY"}`.

### 3. URL Query Parameters

```python
if fake_key in flow.request.url:
    flow.request.url = flow.request.url.replace(fake_key, real_key)
```

Matches in: URLs like `https://api.example.com?key=FAKE_OPENAI_KEY`.

---

## 📁 Project Structure

```
API ProxyGuard/
├── .dockerignore          # Files excluded from Docker build
├── .gitignore             # Files excluded from git
├── Dockerfile             # Container build instructions
├── docker-compose.yml     # Service configuration
├── main.py                # FastAPI web dashboard
├── proxy_script.py        # mitmproxy addon (key swapping logic)
├── data/                  # SQLite database (created at runtime)
└── mitmproxy-ca/          # CA certificate (created at runtime)
```

---

## 🔧 Troubleshooting

### Port 8000 or 8080 already in use

```bash
# Check what's using the port
sudo lsof -i :8000
sudo lsof -i :8080

# Kill the process or change the port mapping in docker-compose.yml
```

### "Connection refused" on localhost:8000

```bash
# Check if the container is running
docker ps | grep proxyguard

# Check the container logs
docker logs <container-id>
```

### "Name or service not known" (502 Bad Gateway)

The container can't resolve DNS. This is usually a Docker DNS issue:

```bash
# Restart Docker
sudo systemctl restart docker

# Or check your /etc/resolv.conf
cat /etc/resolv.conf
```

### CA certificate not generated yet

Make at least **one request through the proxy** first. mitmproxy generates the CA cert on first run.

```bash
curl -k -x http://127.0.0.1:8080 "https://example.com"
```

Then download the cert from the dashboard.

### "Form data requires python-multipart"

This was a bug in earlier versions. Make sure you've rebuilt with the latest code:

```bash
docker compose up -d --build
```

---

## 🔒 Security Notes

- **Default credentials**: Change `PROXY_USER` and `PROXY_PASS` in production
- **Local access only**: Port 8080 is bound to `127.0.0.1` (localhost-only) in docker-compose.yml
- **Database**: The SQLite file is stored at `./data/proxy_vault.db` — keep it secure
- **CA private key**: Located in `./mitmproxy-ca/mitmproxy-ca.pem` — **never share this file**
- **No external dependencies**: The dashboard UI is fully self-contained (no CDN, no external fonts)

---

## 📄 License

This project is provided for educational and personal use. Use responsibly.
```

Now let me commit and push this to GitHub.