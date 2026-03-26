import requests
import time
import hmac
import hashlib
import base64
import os
import re

# 从 GitHub Secrets 中读取环境变量
WEBHOOK = os.environ.get("DINGTALK_WEBHOOK")
SECRET = os.environ.get("DINGTALK_SECRET")
BASE_URL = "https://stock.autoin.me"

def get_sign():
    """钉钉加签逻辑"""
    timestamp = str(round(time.time() * 1000))
    secret_enc = SECRET.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, SECRET)
    hmac_code = hmac.new(secret_enc, string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return timestamp, sign

def send_ding(title, content):
    """发送 Markdown 消息到钉钉"""
    ts, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={ts}&sign={sign}"
    
    # 钉钉限制消息体长度，超过则截断避免发送失败
    if len(content) > 4000:
        content = content[:4000] + "\n\n...(内容较长，已截取)..."

    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "策略深度总结",
            "text": f"### 📍 {title}\n\n{content}\n\n---\n*推送时间: {time.strftime('%Y-%m-%d %H:%M:%S')}*"
        }
    }
    r = requests.post(url, json=data)
    print(f"钉钉接口返回: {r.text}")

def run():
    print("🔄 正在通过后台数据层定位最新时间轴内容...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    
    try:
        # 1. 获取首页索引数据，定位左侧时间轴最顶部的那个链接 (Slug)
        idx_res = requests.get(f"{BASE_URL}/page-data/index/page-data.json", headers=headers, timeout=15)
        idx_data = idx_res.json()
        
        # 获取最新的节点（对应左侧蓝色高亮的时间点）
        latest_node = idx_data['result']['data']['allMarkdownRemark']['edges'][0]['node']
        slug = latest_node['fields']['slug']
        title = latest_node['frontmatter']['title']
        
        full_url = f"{BASE_URL}{slug}"
        print(f"✅ 锁定最新时间点: {title}")

        # 2. 去重检查：如果这个 URL 已经发过了，就退出
        last_url = ""
        if os.path.exists("last_url.txt"):
            with open("last_url.txt", "r") as f: last_url = f.read().strip()
        
        if full_url == last_url:
            print("😴 当前已是最新的内容，无需重复推送。")
            return

        # 3. 模拟“点击”动作：直接请求该页面对应的数据 JSON
        print(f"📖 正在抓取全文内容 (包含经济事件、选项信息等)...")
        content_json_url = f"{BASE_URL}/page-data{slug}page-data.json"
        c_res = requests.get(content_json_url, headers=headers, timeout=15)
        c_data = c_res.json()
        
        # 提取渲染前的原始 HTML 正文
        html_body = c_data['result']['data']['markdownRemark']['html']
        
        # 4. 深度提取并清理格式
        # 将 HTML 标签转换为 Markdown 易读格式
        text = html_body
        text = re.sub(r'<h3>', '\n\n### ', text)
        text = re.sub(r'<h2>', '\n\n## ', text)
        text = re.sub(r'<li>', '\n* ', text)
        text = re.sub(r'</?(p|div|br|span|section|article)>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text) # 剔除所有剩余的 HTML 标签
        
        # 优化排版：压缩多余空行，突出关键词
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        final_text = ""
        for line in lines:
            # 如果是标题类文字，加粗处理
            if any(k in line for k in ["总结", "信息", "选项", "事件", "强调", "提要"]):
                final_text += f"\n\n**{line}**\n"
            else:
                final_text += f"\n{line}"

        # 5. 执行推送并更新记忆文件
        send_ding(title, final_text.strip())
        
        with open("last_url.txt", "w") as f:
            f.write(full_url)
            
        print("🚀 深度内容抓取并推送成功！")

    except Exception as e:
        print(f"💥 运行错误: {str(e)}")

if __name__ == "__main__":
    run()
