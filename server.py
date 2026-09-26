from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime, timedelta
import json
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# ═══════════════════════════════════════════════════════
# ⚙️ НАСТРОЙКИ ПОЧТЫ (берутся из переменных Render)
# ═══════════════════════════════════════════════════════

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@dk.ru")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.mail.ru")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "465"))
EMAIL_FROM = os.environ.get("EMAIL_FROM", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")

ORDERS_FILE = "orders.json"

# ═══════════════════════════════════════════════════════
# ФУНКЦИИ
# ═══════════════════════════════════════════════════════

def load_orders():
    try:
        with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_order(order):
    orders = load_orders()
    order['id'] = len(orders) + 1
    order['created_at'] = datetime.now().isoformat()
    orders.append(order)
    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)
    return order['id']

def send_email(order):
    duration_minutes = int(order.get('durationMinutes', 60))
    hall_price = int(order.get('hallPrice', 0))
    hours = duration_minutes / 60
    hall_cost = int(hours * hall_price)
    
    dishes_price = int(order.get('dishesPrice', 0))
    speaker_cost = 500 if order.get('speaker') else 0
    light_cost = 150 if order.get('light') else 0
    total_cost = hall_cost + dishes_price + speaker_cost + light_cost
    
    date_str = order.get('date', 'Не указана')
    crosses_midnight = order.get('crossesMidnight', False)
    
    if crosses_midnight:
        try:
            start_date = datetime.strptime(date_str, '%Y-%m-%d')
            end_date = start_date + timedelta(days=1)
            date_display = f"{start_date.strftime('%d.%m.%Y')} → {end_date.strftime('%d.%m.%Y')} (следующий день)"
        except:
            date_display = date_str
    else:
        try:
            d = datetime.strptime(date_str, '%Y-%m-%d')
            date_display = d.strftime('%d.%m.%Y')
        except:
            date_display = date_str
    
    subject = f"🎭 Новая заявка ДК: {order.get('eventType', '?')} — {order.get('name', '?')}"
    
    body = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 НОВАЯ ЗАЯВКА НА АРЕНДУ ДК
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏛 ПОМЕЩЕНИЕ: {order.get('hall', '—')}
   Цена: {hall_price:,} ₽/час

🎉 МЕРОПРИЯТИЕ: {order.get('eventType', '—')}

🍽 ПОСУДА: {order.get('dishes', '—')}
   Стоимость: {dishes_price} ₽
   (ущерб 1 ед. — 150 ₽)

🔊 МУЗЫКАЛЬНАЯ КОЛОНКА: {"Да (+500 ₽)" if order.get('speaker') else "Нет"}
💡 СВЕТОВЫЕ ЭФФЕКТЫ: {"Да (+150 ₽)" if order.get('light') else "Нет"}

📅 ДАТА: {date_display}
🕐 ВРЕМЯ: {order.get('startTime', '?')} — {order.get('endTime', '?')}{" (+1 день)" if crosses_midnight else ""}
⏱ ДЛИТЕЛЬНОСТЬ: {duration_minutes} мин. ({hours:.1f} ч.)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 РАСЧЁТ СТОИМОСТИ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Аренда ({hours:.1f} ч × {hall_price:,} ₽): {hall_cost:,} ₽
   Посуда: {dishes_price} ₽
   Колонка: {speaker_cost} ₽
   Свет: {light_cost} ₽
   ─────────────────────
   ИТОГО: {total_cost:,} ₽

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 ЗАКАЗЧИК:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Имя: {order.get('name', '—')}
   Телефон: {order.get('phone', '—')}
   Email: {order.get('email') or 'не указан'}

💬 ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ:
{order.get('comment') or 'нет'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Заявка через веб-форму ДК
Получена: {datetime.now().strftime('%d.%m.%Y %H:%M')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = ADMIN_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    try:
        server = smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT)
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ Письмо отправлено")
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        return False

# ═══════════════════════════════════════════════════════
# МАРШРУТЫ
# ═══════════════════════════════════════════════════════

@app.route('/')
def index():
    return send_from_directory('.', 'form.html')

@app.route('/api/order', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        
        required = ['hall', 'eventType', 'dishes', 'date', 'startTime', 'endTime', 'name', 'phone']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Не заполнено: {field}'}), 400
        
        order_id = save_order(data)
        order_number = f"#DK-{datetime.now().strftime('%m%d')}-{order_id:04d}"
        
        email_sent = send_email(data)
        
        return jsonify({
            'success': True,
            'orderNumber': order_number,
            'orderId': order_id,
            'emailSent': email_sent
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    return jsonify(load_orders())

if __name__ == '__main__':
    print("🚀 Сервер ДК запущен на http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
