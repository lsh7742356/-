import requests
import time
import hmac
import hashlib
import base64
import os

WEBHOOK = os.environ.get("DINGTALK_WEBHOOK")
SECRET = os.environ.get("DINGTALK_SECRET")

def get_sign():
    timestamp = str(round(time.time() * 1000))
    secret_enc = SECRET.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, SECRET)
    hmac_code = hmac.new(secret_enc, string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return timestamp, sign

def send_ding(title, content):
    ts, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={ts}&sign={sign}"
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "策略更新",
            "text": f"# {title}\n\n{content}\n\n---\n*推送时间: {time.strftime('%H:%M:%S', time.localtime())}*"
        }
    }
    r = requests.post(url, json=data)
    print(f"钉钉反馈: {r.text}")

def run():
    print("🚀 正在通过 API 获取最新总结数据...")
    try:
        # 直接抓取网站背后的 JSON 数据接口
        api_url = "https://stock.autoin.me/api/summaries/latest"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        # 如果 API 不通，尝试备用地址
        res = requests.get(api_url, headers=headers, timeout=20)
        if res.status_code != 200:
            # 备用方案：抓取主页并手动定位最新的 slug
            res = requests.get("https://stock.autoin.me/page-data/index/page-data.json", headers=headers)
            data = res.json()
            latest_node = data['result']['data']['allMarkdownRemark']['edges'][0]['node']
            slug = latest_node['fields']['slug']
            title = latest_node['frontmatter']['title']
        else:
            data = res.json()
            slug = data['slug']
            title = data['title']

        full_url = f"https://stock.autoin.me{slug}"
        print(f"✅ 找到最新页面: {title}")

        # 检查是否重复
        last_url = ""
        if os.path.exists("last_url.txt"):
            with open("last_url.txt", "r") as f: last_url = f.read().strip()
        if full_url == last_url:
            print("😴 内容已推送，跳过。")
            return

        # 获取该页面的具体内容
        # 针对 Gatsby/Next.js 类网站获取 JSON 内容块
        content_url = f"https://stock.autoin.me/page-data{slug}page-data.json"
        c_res = requests.get(content_url, headers=headers)
        c_data = c_res.json()
        
        # 提取 HTML 文本
        html_content = c_data['result']['data']['markdownRemark']['html']
        
        # 简单清洗 HTML 标签
        import re
        text_content = re.sub('<[^<]+?>', '', html_content) # 去掉所有 HTML 标签
        text_content = text_content.replace('聊天总结', '### 聊天总结').replace('具体信息', '\n--- \n### 具体信息')

        send_ding(title, text_content)
        
        with open("last_url.txt", "w") as f: f.write(full_url)
        print("✅ 全文推送成功！")

    except Exception as e:
        print(f"💥 运行错误: {e}")
        print("建议：如果此 API 方案失效，请联系我确认该网站的确切数据接口。")

if __name__ == "__main__":
    run()
