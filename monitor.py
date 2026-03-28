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
    """临时测试版：清晰区分标题和内容"""
    ts, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={ts}&sign={sign}"
   
    # 1. 主标题处理（最顶部的大标题）
    content = re.sub(r'^#\s*(.+?)$', r'\n\n### **📌 \1**', content, flags=re.MULTILINE, count=1)
    
    # 2. 二级标题（如 ## 聊天总结）
    content = re.sub(r'^##\s*(.+?)$', r'\n\n### **📌 \1**', content, flags=re.MULTILINE)
    
    # 3. 三级标题（如 ### 操作策略）
    content = re.sub(r'^###\s*(.+?)$', r'\n\n#### **📌 \1**', content, flags=re.MULTILINE)
    
    # 项目符号优化
    content = content.replace("•", "\n* ")
    
    # 在每个加粗标题后增加换行，让标题和内容更清晰分开
    content = re.sub(r'(\*\*📌 .+?\*\*)', r'\n\n\1\n', content)
    
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "财经摘要更新",
            "text": f"{content}\n\n---\n*🕒 本次更新北京时间: {beijing_time}*"
        }
    }
    requests.post(url, json=data)

def extract_beijing_time(text):
    """提取北京时间（仅用于显示，不用于去重）"""
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
        
        current_time = extract_beijing_time(raw_text) or bj_now + ":00"
        print(f"📍 当前页面北京时间: {current_time}")
        
        # === 临时测试模式：每次都推送（关闭去重）===
        print("🔧 当前为临时测试模式 → 每次都推送（用于测试标题排版）")
        
        # 执行推送
        send_ding(raw_text, current_time)
        
        print(f"🚀 已推送！（测试模式）")
        
    except Exception as e:
        print(f"💥 运行异常: {str(e)}")

if __name__ == "__main__":
    run()
