import requests
import time
import hmac
import hashlib
import base64
import os
from datetime import datetime
import pytz  # 处理美股时区必备
from bs4 import BeautifulSoup

# --- 1. 基础配置 (从 GitHub Secrets 读取) ---
WEBHOOK = os.environ.get("DINGTALK_WEBHOOK")
SECRET = os.environ.get("DINGTALK_SECRET")
BASE_URL = "https://stock.autoin.me"

def is_market_open():
    """判断美股是否开盘（纽约时间）"""
    # 获取纽约当前时间
    tz_ny = pytz.timezone('America/New_York')
    now_ny = datetime.now(tz_ny)
    
    # 周六(5)和周日(6)不运行
    if now_ny.weekday() >= 5:
        print(f"😴 纽约时间 {now_ny.strftime('%Y-%m-%d %H:%M')}: 周末休市，不运行。")
        return False
        
    # 交易时段判断：纽约时间 09:00 - 17:00 (涵盖盘前、盘中、盘后初期)
    # 如果你想改时间，调整下面这两个数字即可
    current_hour = now_ny.hour
    if 9 <= current_hour < 17:
        print(f"🕒 纽约时间 {now_ny.strftime('%H:%M')}: 属于交易监控时段。")
        return True
    else:
        print(f"🌙 纽约时间 {now_ny.strftime('%H:%M')}: 非交易监控时段，不运行。")
        return False

def get_sign():
    """钉钉加签认证"""
    timestamp = str(round(time.time() * 1000))
    secret_enc = SECRET.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, SECRET)
    hmac_code = hmac.new(secret_enc, string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    return timestamp, base64.b64encode(hmac_code).decode('utf-8')

def send_ding(content):
    """发送排版好的 Markdown 消息到钉钉"""
    ts, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={ts}&sign={sign}"
    
    # 关键词美化
    content = content.replace("聊天总结", "## 📝 聊天总结")
    content = content.replace("具体信息", "--- \n### 🔍 具体信息")
    content = content.replace("选项信息", "--- \n### 📊 选项信息")
    content = content.replace("经济事件", "--- \n### 📅 经济事件")
    
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "财经更新推送",
            "text": f"{content}\n\n---\n*🕒 推送时间(北京): {datetime.now().strftime('%m-%d %H:%M')}*"
        }
    }
    r = requests.post(url, json=data)
    print(f"钉钉接口返回: {r.text}")

def run():
    # A. 检查美股时间，不开盘直接退出
    if not is_market_open():
        return

    print("🌐 正在连接网站首页抓取全文...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # B. 抓取首页
        res = requests.get(BASE_URL, headers=headers, timeout=20)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # C. 提取正文内容
        main_body = soup.find('main') or soup.find('body')
        raw_text = main_body.get_text(separator="\n", strip=True)
        
        # D. 过滤：只拿从“聊天总结”开始的内容
        if "聊天总结" in raw_text:
            useful_content = raw_text[raw_text.find("聊天总结"):]
        else:
            useful_content = raw_text[:3000]

        # E. 去重逻辑：内容变了才发
        content_hash = hashlib.md5(useful_content.encode('utf-8')).hexdigest()
        hash_file = "last_content_hash.txt"
        
        last_hash = ""
        if os.path.exists(hash_file):
            with open(hash_file, "r") as f:
                last_hash = f.read().strip()
        
        if content_hash == last_hash:
            print("😴 内容与上次完全一致，跳过推送。")
            return

        # F. 执行发送并更新记录
        send_ding(useful_content)
        with open(hash_file, "w") as f:
            f.write(content_hash)
        print("🚀 检测到内容更新，已成功推送到钉钉！")

    except Exception as e:
        print(f"💥 运行中出错: {str(e)}")

if __name__ == "__main__":
    run()
