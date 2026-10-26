import os
import sys
import json
import time
import datetime
import urllib.request
import urllib.error

# Ensure utf-8 output on all platforms
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Config & Environment variables
BASE_URL = os.environ.get("MEOWLIX_URL", "https://freegp.meowlix.cc").rstrip("/")
API_KEY = os.environ.get("MEOWLIX_API_KEY", "").strip()
SERVER_ID = os.environ.get("SERVER_ID", "").strip() # Optional: if empty, auto-detect all servers
COOKIES = os.environ.get("MEOWLIX_COOKIES", "").strip() # Optional: for Playwright browser screenshot
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "").strip()
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "").strip()

def send_telegram_notification(message: str, image_path: str = None):
    """Send status message and optional screenshot to Telegram."""
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("[INFO] TG_BOT_TOKEN or TG_CHAT_ID not provided. Skipping Telegram notification.")
        return

    if image_path and os.path.exists(image_path):
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto"
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        
        with open(image_path, "rb") as f:
            photo_data = f.read()
            
        data = bytearray()
        def add_field(name, value):
            data.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
            
        add_field("chat_id", TG_CHAT_ID)
        add_field("caption", message)
        add_field("parse_mode", "HTML")
        
        data.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"screenshot.png\"\r\nContent-Type: image/png\r\n\r\n".encode())
        data.extend(photo_data)
        data.extend(f"\r\n--{boundary}--\r\n".encode())
        
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Mozilla/5.0"
        })
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                print("[INFO] Telegram photo notification sent successfully!")
                return
        except Exception as e:
            print(f"[WARN] Failed to send Telegram photo: {e}, falling back to text message...")

    # Fallback to text message
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TG_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print("[INFO] Telegram text notification sent successfully!")
    except Exception as e:
        print(f"[ERROR] Failed to send Telegram message: {e}")

def api_request(path: str, method: str = "GET", data: dict = None):
    """Helper to perform Pterodactyl client API requests."""
    url = f"{BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    encoded_data = None
    if method in ["POST", "PUT", "PATCH"]:
        headers["Content-Type"] = "application/json"
        encoded_data = json.dumps(data or {}).encode("utf-8")
        
    req = urllib.request.Request(url, headers=headers, data=encoded_data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        try:
            err_json = json.loads(err_body)
            detail = err_json.get("errors", [{}])[0].get("detail", err_body)
        except Exception:
            detail = err_body
        return {"error": True, "status": e.code, "detail": detail}
    except Exception as e:
        return {"error": True, "detail": str(e)}

def get_servers():
    """Get all servers belonging to the user."""
    res = api_request("/api/client")
    if res.get("error"):
        print(f"[ERROR] Failed to list servers: {res.get('detail')}")
        return []
    servers = []
    for item in res.get("data", []):
        attrs = item.get("attributes", {})
        servers.append({
            "identifier": attrs.get("identifier"),
            "uuid": attrs.get("uuid"),
            "name": attrs.get("name"),
            "node": attrs.get("node")
        })
    return servers

def check_and_renew(server: dict):
    """Check renewal status and renew if eligible."""
    identifier = server["identifier"]
    name = server["name"]
    node = server.get("node", "Unknown")
    
    print(f"\n[INFO] Checking server: {name} ({identifier}) on {node}...")
    
    # 1. Query renewal status
    status_res = api_request(f"/api/client/dezerx/server-create/{identifier}/renewal")
    if status_res.get("error"):
        print(f"[ERROR] Could not fetch renewal status for {name}: {status_res.get('detail')}")
        return {
            "success": False,
            "server": server,
            "message": f"获取续期状态失败: {status_res.get('detail')}"
        }
        
    renew_at = status_res.get("renewAt")
    is_renewable = status_res.get("renewable", False)
    is_overdue = status_res.get("overdue", False)
    is_suspended = status_res.get("suspended", False)
    renewals_count = status_res.get("renewals", 0)
    
    print(f"  - 到期时间 (renewAt): {renew_at}")
    print(f"  - 是否可续期 (renewable): {is_renewable}")
    print(f"  - 逾期状态 (overdue): {is_overdue}")
    print(f"  - 暂停状态 (suspended): {is_suspended}")
    print(f"  - 已续期次数: {renewals_count}")
    
    action_taken = "未触发"
    renew_result_msg = ""
    
    # 2. Renew if eligible or overdue
    if is_renewable or is_overdue or is_suspended:
        print(f"[INFO] Server {name} is eligible for renewal! Submitting renewal request...")
        renew_res = api_request(f"/api/client/dezerx/server-create/{identifier}/renew", method="POST")
        if not renew_res.get("error"):
            action_taken = "续期成功 ✅"
            renew_at = renew_res.get("renewAt", renew_at)
            renew_result_msg = f"服务器已成功续期！新的到期时间: {renew_at}"
            print(f"[SUCCESS] {renew_result_msg}")
        else:
            action_taken = "续期失败 ❌"
            renew_result_msg = f"续期请求失败: {renew_res.get('detail')}"
            print(f"[ERROR] {renew_result_msg}")
    else:
        action_taken = "未到期无需续期 ⏳"
        renew_result_msg = "当前未进入续期窗口（通常在剩余天数不足时开放续期），暂无需操作。"
        print(f"[INFO] {renew_result_msg}")
        
    return {
        "success": True,
        "server": server,
        "renew_at": renew_at,
        "is_renewable": is_renewable,
        "action_taken": action_taken,
        "detail": renew_result_msg
    }

def capture_screenshot(server_id: str, output_path: str = "screenshot.png"):
    """Use Playwright to capture screenshot of server page if cookies are provided."""
    if not COOKIES:
        print("[INFO] MEOWLIX_COOKIES not provided. Will generate high-res status card instead.")
        return False
        
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[WARN] Playwright not installed. Skipping browser screenshot.")
        return False
        
    print("[INFO] Launching Playwright to capture webpage screenshot...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            
            # Parse and set cookies
            cookie_list = []
            for item in COOKIES.split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    cookie_list.append({
                        "name": k,
                        "value": v,
                        "domain": "freegp.meowlix.cc",
                        "path": "/"
                    })
            context.add_cookies(cookie_list)
            page = context.new_page()
            target_url = f"{BASE_URL}/server/{server_id}"
            page.goto(target_url, timeout=30000, wait_until="networkidle")
            page.wait_for_timeout(3000)
            page.screenshot(path=output_path, full_page=False)
            browser.close()
            print(f"[SUCCESS] Webpage screenshot saved to {output_path}")
            return True
    except Exception as e:
        print(f"[WARN] Playwright screenshot failed: {e}")
        return False

def generate_status_card(result_list: list, output_path: str = "screenshot.png"):
    """Generate a high-quality status card image if browser screenshot is not available."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("[WARN] Pillow not installed, skipping card generation.")
        return False

    width, height = 900, 480
    image = Image.new("RGB", (width, height), color=(18, 18, 24))
    draw = ImageDraw.Draw(image)

    # Gradient-like top accent bar
    draw.rectangle([0, 0, width, 8], fill=(182, 143, 255))
    
    # Header
    draw.text((40, 35), "MEOWLIX SERVER RENEW REPORT", fill=(182, 143, 255))
    draw.text((40, 65), f"Auto-Renew Scheduled Run · {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill=(140, 140, 160))

    # Divider
    draw.line([(40, 105), (width - 40, 105)], fill=(40, 40, 55), width=2)

    y = 125
    for res in result_list:
        srv = res.get("server", {})
        name = srv.get("name", "Unknown Server")
        identifier = srv.get("identifier", "Unknown ID")
        node = srv.get("node", "Japan")
        renew_at = res.get("renew_at", "N/A")
        action = res.get("action_taken", "N/A")
        
        # Server card background
        draw.rounded_rectangle([40, y, width - 40, y + 150], radius=12, fill=(28, 28, 38), outline=(60, 60, 80))
        
        # Server title
        draw.text((60, y + 18), f"{name}", fill=(240, 240, 255))
        draw.text((60, y + 48), f"ID: {identifier}  |  Node: {node}", fill=(140, 140, 160))
        
        # Status details
        action_color = (100, 220, 140) if "成功" in action or "Success" in action else ((255, 200, 80) if "未到期" in action or "Pending" in action else (255, 100, 100))
        status_text = "Pending Renewal (Not Due Yet)" if not res.get("is_renewable") else "Renewed Successfully"
        
        draw.text((60, y + 80), f"Expires: {renew_at}", fill=(200, 200, 220))
        draw.text((60, y + 110), f"Status:  {status_text}", fill=action_color)
        
        y += 170

    # Footer
    draw.text((40, height - 35), "Pterodactyl / DezerX Free Server Auto-Renew Bot", fill=(90, 90, 110))

    image.save(output_path)
    print(f"[SUCCESS] Status card image saved to {output_path}")
    return True

def main():
    if not API_KEY:
        print("[FATAL] MEOWLIX_API_KEY environment variable is required!")
        sys.exit(1)

    print("==================================================")
    print("   🐱 Meowlix 服务器自动续期与监控脚本")
    print("==================================================")
    
    # 1. Get targets
    if SERVER_ID:
        servers = [{"identifier": SERVER_ID, "name": f"Server {SERVER_ID}"}]
    else:
        servers = get_servers()
        if not servers:
            print("[WARN] No servers returned from API, falling back to 31becfe1")
            servers = [{"identifier": "31becfe1", "name": "Free python generic"}]

    print(f"[INFO] Found {len(servers)} server(s) to process.")
    
    results = []
    for srv in servers:
        res = check_and_renew(srv)
        results.append(res)
        time.sleep(1)

    # 2. Screenshot handling
    screenshot_path = "screenshot.png"
    has_image = False
    
    primary_id = servers[0]["identifier"]
    if COOKIES:
        has_image = capture_screenshot(primary_id, screenshot_path)
        
    if not has_image:
        has_image = generate_status_card(results, screenshot_path)

    # 3. Assemble Telegram notification message
    tg_lines = [
        "<b>🐱 Meowlix 服务器自动续期报告</b>",
        f"⏰ 执行时间: <code>{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>",
        "━━━━━━━━━━━━━━━━━━━━"
    ]
    
    for res in results:
        srv = res.get("server", {})
        name = srv.get("name", "Unknown")
        identifier = srv.get("identifier", "Unknown")
        renew_at = res.get("renew_at", "N/A")
        action = res.get("action_taken", "N/A")
        detail = res.get("detail", "")
        
        tg_lines.append(f"🖥️ <b>服务器</b>: <code>{name}</code> (<code>{identifier}</code>)")
        tg_lines.append(f"⏳ <b>到期时间</b>: <code>{renew_at}</code>")
        tg_lines.append(f"📌 <b>操作结果</b>: <b>{action}</b>")
        tg_lines.append(f"💬 <b>说明</b>: {detail}")
        tg_lines.append("────────────────────")

    tg_msg = "\n".join(tg_lines)

    # 4. Send TG notification
    send_telegram_notification(tg_msg, screenshot_path if has_image else None)
    print("\n[INFO] All tasks finished.")

if __name__ == "__main__":
    main()
