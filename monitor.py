import requests
import time
import hmac
import hashlib
import base64
import os
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# 配置信息
WEBHOOK = os.environ.get("DINGTALK_WEBHOOK")
SECRET = os.environ.get("DINGTALK_SECRET")
BASE_URL = "https://stock.autoin.me"

def is_bj_workday():
    """判断当前是否为北京时间的周一至周五"""
    tz_bj = pytz.timezone('Asia/Shanghai')
    now_bj = datetime.now(tz_bj)
    
    # weekday(): 0是周一, 4是周五, 5是周六, 6是周日
    if now_bj.weekday() <= 4:
        print(f"✅ 北京时间 {now_bj.strftime('%Y-%m-%d %H:%M')}: 工作日监控中...")
        return True
    else:
        print(f"☕ 北京时间 {now_bj.strftime('%Y-%m-%d %H:%M')}: 周末休息，暂不推送。")
        return False

def get_sign():
    timestamp = str(round(time.time() * 1000))
    secret_enc = SECRET.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, SECRET)
    hmac_code = hmac.new(secret_enc, string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    return timestamp, base64.b64encode(hmac_code).decode('utf-8')

def send_ding(content):
    """发送排版优化后的消息"""
    ts, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={ts}&sign={sign}"
    
    # 标题加粗与格式优化
    content = content.replace("聊天总结", "\n\n### **📌 聊天总结**\n")
    content = content.replace("具体信息", "\n\n### **🔍 具体信息**\n")
    content = content.replace("选项信息", "\n\n### **📊 选项信息**\n")
    content = content.replace("经济事件", "\n\n### **📅 经济事件**\n")
    content = content.replace("•", "\n* ")

    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "财经摘要更新",
            "text": f"{content}\n\n---\n*🕒 监控时间(北京): {datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%m-%d %H:%M')}*"
        }
    }
    requests.post(url, json=data)

def run():
    # 只有北京时间周一到周五才运行
    if not is_bj_workday():
        return

    print("🌐 正在抓取网站内容...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        res = requests.get(BASE_URL, headers=headers, timeout=20)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        main_body = soup.find('main') or soup.find('body')
        raw_text = main_body.get_text(separator="\n", strip=True)
        
        # 截取核心内容
        if "聊天总结" in raw_text:
            useful_content = raw_text[raw_text.find("聊天总结"):]
        else:
            useful_content = raw_text[:3000]

        # 核心去重逻辑
        content_hash = hashlib.md5(useful_content.encode('utf-8')).hexdigest()
        hash_file = "last_content_hash.txt"
        last_hash = ""
        if os.path.exists(hash_file):
            with open(hash_file, "r") as f:
                last_hash = f.read().strip()
        
        if content_hash == last_hash:
            print("😴 内容没有更新，保持安静。")
            return

        # 执行推送
        send_ding(useful_content)
        
        # 记录新内容的指纹
        with open(hash_file, "w") as f:
            f.write(content_hash)
        print("🚀 检测到内容更新，已推送到钉钉！")

    except Exception as e:
        print(f"💥 运行异常: {str(e)}")

if __name__ == "__main__":
    run()
