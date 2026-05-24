import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import re

URL = "http://www.wap.cnyiot.com/nat/pay.aspx?mid=19103082509"
DATA_FILE = "data/power_data.json"
ALERT_THRESHOLD = 20  # 低于20度时提醒

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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
        }
        response = requests.get(URL, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取数据
        text = soup.get_text()
        
        # 使用正则表达式提取数字
        remaining_kwh = None
        remaining_yuan = None
        price = None
        
        # 匹配剩余电量: XX.XX kWh
        kwh_match = re.search(r'剩余电量[：:]?\s*([\d.]+)\s*kWh', text, re.IGNORECASE)
        if kwh_match:
            remaining_kwh = float(kwh_match.group(1))
        
        # 匹配剩余金额: XX.XX 元
        yuan_match = re.search(r'剩余金额[：:]?\s*([\d.]+)\s*元', text)
        if yuan_match:
            remaining_yuan = float(yuan_match.group(1))
        
        # 匹配综合费用
        price_match = re.search(r'综合费用[：:]?\s*([\d.]+)\s*元[/每]?kWh', text)
        if price_match:
            price = float(price_match.group(1))
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "remaining_kwh": remaining_kwh,
            "remaining_yuan": remaining_yuan,
            "price_per_kwh": price,
            "raw_text": text[:500]  # 保存部分原始文本用于调试
        }
        
        return data
        
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
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
    
    # 只保留最近30天的数据
    all_data = all_data[-1440:]  # 30天 * 48次/天
    
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"数据已保存: {data}")

def check_alert(data):
    """检查是否需要发送低电量提醒"""
    remaining = data.get('remaining_kwh')
    if remaining and remaining < ALERT_THRESHOLD:
        title = f"⚠️ 电量不足提醒 - 仅剩 {remaining} 度"
        content = f"""当前电量: {remaining} kWh
剩余金额: {data.get('remaining_yuan')} 元
时间: {data['timestamp']}

请及时充值！"""
        send_wechat_notification(title, content)
        print(f"已发送低电量提醒: {remaining} kWh")

def main():
    print(f"开始监控... {datetime.now()}")
    
    data = fetch_power_info()
    save_data(data)
    check_alert(data)
    
    if data.get('error'):
        print(f"错误: {data['error']}")
        exit(1)
    
    print(f"监控完成: 剩余电量 {data.get('remaining_kwh')} kWh")

if __name__ == "__main__":
    main()