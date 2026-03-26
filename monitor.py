import requests, time, hmac, hashlib, base64, os
from bs4 import BeautifulSoup

# 从 Secrets 读取钥匙
WEBHOOK = os.environ.get("DINGTALK_WEBHOOK")
SECRET = os.environ.get("DINGTALK_SECRET")
BASE_URL = "https://stock.autoin.me"

def get_sign():
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f'{timestamp}\n{SECRET}'
    hmac_code = hmac.new(SECRET.encode('utf-8'), string_to_sign.encode('utf-8'), hashlib.sha256).digest()
    return timestamp, base64.b64encode(hmac_code).decode('utf-8')

def send_ding(content):
    ts, sign = get_sign()
    requests.post(f"{WEBHOOK}&timestamp={ts}&sign={sign}", json={"msgtype": "text", "text": {"content": content}})

def run():
    try:
        res = requests.get(BASE_URL, timeout=15)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        link_node = soup.select_one('a[href*="/summaries/"]')
        if not link_node: return False
        
        latest_url = BASE_URL + link_node['href']
        last_url = open("last_url.txt", "r").read().strip() if os.path.exists("last_url.txt") else ""
        
        if latest_url != last_url:
            detail = requests.get(latest_url, timeout=15)
            detail.encoding = 'utf-8'
            raw_text = BeautifulSoup(detail.text, 'html.parser').get_text(separator="\n", strip=True)
            full_message = f"【小赵策略总结更新】\n链接：{latest_url}\n\n{raw_text}"
            send_ding(full_message[:15000]) 
            with open("last_url.txt", "w") as f: f.write(latest_url)
            return True
    except Exception as e:
        print(f"出错: {e}")
    return False

if __name__ == "__main__":
    if run():
        os.system('git config --global user.email "bot@github.com"')
        os.system('git config --global user.name "StockBot"')
        os.system('git add last_url.txt && git commit -m "update" && git push')
