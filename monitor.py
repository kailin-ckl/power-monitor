import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import re
import sys
import pytz

URL = "http://www.wap.cnyiot.com/nat/pay.aspx?mid=19103082509"
DATA_FILE = "data/power_data.json"
ALERT_THRESHOLD = 10

# 设置中国时区
CHINA_TZ = pytz.timezone('Asia/Shanghai')

def get_china_time():
    """获取中国时区时间"""
    return datetime.now(CHINA_TZ)

def safe_console_text(text):
    """返回当前控制台可安全输出的文本"""
    encoding = sys.stdout.encoding or 'utf-8'
    return str(text).encode(encoding, errors='replace').decode(encoding)

def send_wechat_notification(title, content):
    """使用Server酱发送微信通知"""
    sckey = os.environ.get('SCKEY')
    if not sckey:
        return

    url = f"https://sctapi.ftqq.com/{sckey}.send"
    data = {
        "title": title,
        "desp": content
    }
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"通知发送失败: {e}")

def fetch_power_info():
    """抓取电量信息"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        response = requests.get(URL, headers=headers, timeout=15, allow_redirects=True)
        response.encoding = 'utf-8'

        print(f"状态码: {response.status_code}")
        print(f"URL: {response.url}")
        print(f"内容长度: {len(response.text)}")

        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()

        print(f"页面内容预览: {safe_console_text(text[:300])}")

        remaining_kwh = None
        remaining_yuan = None
        price = None

        kwh_match = re.search(r'剩余电量[：:]?\s*([\d.]+)\s*kWh', text, re.IGNORECASE)
        if kwh_match:
            remaining_kwh = float(kwh_match.group(1))

        yuan_match = re.search(r'剩余金额[：:]?\s*([\d.]+)\s*元', text)
        if yuan_match:
            remaining_yuan = float(yuan_match.group(1))

        price_match = re.search(r'综合费用[：:]?\s*([\d.]+)\s*元[/每]?kWh', text)
        if price_match:
            price = float(price_match.group(1))

        data = {
            "timestamp": get_china_time().isoformat(),
            "remaining_kwh": remaining_kwh,
            "remaining_yuan": remaining_yuan,
            "price_per_kwh": price,
            "raw_preview": text[:200]
        }

        return data

    except Exception as e:
        return {
            "timestamp": get_china_time().isoformat(),
            "error": str(e)
        }

def save_data(data):
    """保存数据到JSON文件"""
    os.makedirs("data", exist_ok=True)

    all_data = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            all_data = json.load(f)

    all_data.append(data)
    all_data = all_data[-1440:]

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

def check_alert(data):
    """检查是否需要发送低电量提醒"""
    remaining = data.get('remaining_kwh')
    if remaining is not None and remaining < ALERT_THRESHOLD:
        title = f"⚠️ 电量不足提醒 - 仅剩 {remaining} 度"
        content = f"""当前电量: {remaining} kWh
剩余金额: {data.get('remaining_yuan')} 元
时间: {data['timestamp']}

请及时充值！"""
        send_wechat_notification(title, content)
        print(f"已发送低电量提醒: {remaining} kWh")

def main():
    print(f"开始监控... {get_china_time()}")

    data = fetch_power_info()
    save_data(data)
    check_alert(data)

    if data.get('error'):
        print(f"错误: {data['error']}")
        exit(1)

    print(f"监控完成: 剩余电量 {data.get('remaining_kwh')} kWh")
    print(f"时间: {data['timestamp']}")

if __name__ == "__main__":
    main()
