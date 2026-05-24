import json
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os
import pytz
import matplotlib

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

DATA_FILE = "data/power_data.json"
CHINA_TZ = pytz.timezone('Asia/Shanghai')

def get_china_time():
    return datetime.now(CHINA_TZ)

def load_data():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_excel(data):
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    # 移除时区信息，避免Excel不支持
    df['timestamp'] = df['timestamp'].dt.tz_localize(None)
    df = df.dropna(subset=['remaining_kwh'])

    if len(df) == 0:
        print("没有有效数据，无法生成报告")
        return None

    filename = f"电量报告_{get_china_time().strftime('%Y%m%d')}.xlsx"
    writer = pd.ExcelWriter(filename, engine='openpyxl')

    # 第一页：走势图
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df['timestamp'], df['remaining_kwh'], marker='o', linewidth=2, markersize=3)
    ax.set_title('电量使用走势图', fontsize=16)
    ax.set_xlabel('时间', fontsize=12)
    ax.set_ylabel('剩余电量 (kWh)', fontsize=12)
    ax.yaxis.set_major_locator(MultipleLocator(1))
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()

    chart_path = 'chart.png'
    plt.savefig(chart_path, dpi=150)
    plt.close()

    from openpyxl import load_workbook
    from openpyxl.drawing.image import Image as XLImage

    df_chart = pd.DataFrame({'说明': ['今日电量使用走势图']})
    df_chart.to_excel(writer, sheet_name='走势图', index=False)

    workbook = writer.book
    worksheet = writer.sheets['走势图']
    img = XLImage(chart_path)
    img.width = 720
    img.height = 360
    worksheet.add_image(img, 'A3')

    # 第二页：详情数据
    df_display = df[['timestamp', 'remaining_kwh', 'remaining_yuan', 'price_per_kwh']].copy()
    df_display.columns = ['时间', '剩余电量(kWh)', '剩余金额(元)', '单价(元/kWh)']
    df_display.to_excel(writer, sheet_name='详情数据', index=False)

    writer.close()

    if os.path.exists(chart_path):
        os.remove(chart_path)

    return filename

def send_email(filename):
    email_password = os.environ.get('EMAIL_PASSWORD')
    email_to = os.environ.get('EMAIL_TO', '2788590428@qq.com')
    email_from = os.environ.get('EMAIL_FROM', '2788590428@qq.com')

    if not email_password:
        print("未配置邮箱密码，跳过发送邮件")
        return

    msg = MIMEMultipart()
    msg['From'] = email_from
    msg['To'] = email_to
    msg['Subject'] = f'电量日报 - {get_china_time().strftime("%Y年%m月%d日")}'

    body = f'''
    您好！

    附件是今日电量使用报告，包含：
    - 走势图：显示今日电量变化趋势
    - 详情数据：每10分钟的电量记录

    报告生成时间：{get_china_time().strftime("%Y-%m-%d %H:%M:%S")}
    '''
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    with open(filename, 'rb') as f:
        attachment = MIMEBase('application', 'octet-stream')
        attachment.set_payload(f.read())

    encoders.encode_base64(attachment)
    attachment.add_header(
        'Content-Disposition',
        f'attachment; filename= {filename}'
    )
    msg.attach(attachment)

    server = smtplib.SMTP('smtp.qq.com', 587)
    server.starttls()
    server.login(email_from, email_password)
    server.send_message(msg)
    server.quit()

    print(f"邮件已发送至 {email_to}")

def main():
    print(f"开始生成报告... {get_china_time()}")

    if not os.path.exists(DATA_FILE):
        print("数据文件不存在")
        return

    data = load_data()

    if len(data) == 0:
        print("没有数据")
        return

    filename = generate_excel(data)
    if filename:
        print(f"报告已生成: {filename}")
        send_email(filename)

        if os.path.exists(filename):
            os.remove(filename)
            print("本地报告文件已清理")

if __name__ == "__main__":
    main()
