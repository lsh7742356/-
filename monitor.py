import requests
import re
import os
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# 配置信息
WEBHOOK = os.environ.get("DINGTALK_WEBHOOK")
SECRET = os.environ.get("DINGTALK_SECRET")
BASE_URL = "https://stock.autoin.me"

def get_sign():
    timestamp = str(round(time.time() * 1000))
    secret_enc = SECRET.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, SECRET)
    hmac_code = hmac.new(secret_enc, string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    return timestamp, base64.b64encode(hmac_code).decode('utf-8')

def send_ding(content, beijing_time):
    """推送优化：保留网页原始结构，只做轻度美化"""
    ts, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={ts}&sign={sign}"
   
    # 1. 把网页主标题（第一行）突出显示为大标题
    content = re.sub(r'^#\s*(.+?)$', r'\n\n### **📌 \1**', content, flags=re.MULTILINE, count=1)
    
    # 2. 处理常见的二级标题（## 开头）
    content = re.sub(r'^##\s*(.+?)$', r'\n\n### **📌 \1**', content, flags=re.MULTILINE)
    
    # 3. 处理三级标题（### 开头）
    content = re.sub(r'^###\s*(.+?)$', r'\n\n#### **📌 \1**', content, flags=re.MULTILINE)
    
    # 项目符号优化
    content = content.replace("•", "\n* ")
    
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "财经摘要更新",
            "text": f"{content}\n\n---\n*🕒 本次更新北京时间: {beijing_time}*"
        }
    }
    requests.post(url, json=data)

def extract_beijing_time(text):
    """只以北京时间作为去重唯一标准"""
    patterns = [
        r'北京时间[：:]\s*([\d\-:\sCST]+)',
        r'北京时间[:：]\s*([0-9\-:\s]+)',
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s*CST)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None

def run():
    bj_now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M')
    print(f"🌐 北京时间 {bj_now} 开始监测...")

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
   
    try:
        res = requests.get(BASE_URL, headers=headers, timeout=20)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        main_body = soup.find('main') or soup.find('body')
        raw_text = main_body.get_text(separator="\n", strip=True)
        
        current_time = extract_beijing_time(raw_text)
        if not current_time:
            current_time = bj_now + ":00"
        
        print(f"📍 当前页面北京时间: {current_time}")
        
        # 去重：只看北京时间
        time_file = "last_beijing_time.txt"
        last_time = ""
        if os.path.exists(time_file):
            with open(time_file, "r", encoding="utf-8") as f:
                last_time = f.read().strip()
        
        if current_time == last_time:
            print("😴 北京时间未变化 → 内容相同，不推送")
            return
        
        # 执行推送（保留原始结构）
        send_ding(raw_text, current_time)
        
        # 保存新时间
        with open(time_file, "w", encoding="utf-8") as f:
            f.write(current_time)
        
        print(f"🚀 北京时间已更新 → 已推送！")
        
    except Exception as e:
        print(f"💥 运行异常: {str(e)}")

if __name__ == "__main__":
    run()
