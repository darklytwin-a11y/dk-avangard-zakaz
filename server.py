import os
import json
from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime

app = Flask(__name__)

# ═══════════════════════════════════════════════════════
# ⚙️ НАСТРОЙКИ
# ═══════════════════════════════════════════════════════

ORDERS_FILE = "orders.json"

# ═══════════════════════════════════════════════════════
# ФУНКЦИИ
# ═══════════════════════════════════════════════════════

def load_orders():
    try:
        with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_order(order):
    try:
        orders = load_orders()
        order['id'] = len(orders) + 1
        order['created_at'] = datetime.now().isoformat()
        orders.append(order)
        with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
        return order['id']
    except Exception as e:
        print(f"⚠️ Не удалось сохранить в файл: {e}")
        return int(datetime.now().timestamp()) % 100000

# ═══════════════════════════════════════════════════════
# МАРШРУТЫ
# ═══════════════════════════════════════════════════════

@app.route('/')
def index():
    return send_from_directory('.', 'form.html')

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

# ═══════════════════════════════════════════════════════
# 🖼 СТАТИКА (логотип и другие картинки)
# ═══════════════════════════════════════════════════════
@app.route('/<path:filename>')
def serve_static(filename):
    """Отдаёт любые файлы из корня репозитория (logo.png и т.д.)"""
    try:
        return send_from_directory('.', filename)
    except Exception:
        return "Файл не найден", 404

# ═══════════════════════════════════════════════════════
# API ЗАЯВОК
# ═══════════════════════════════════════════════════════

@app.route('/api/order', methods=['POST'])
def create_order():
    try:
        data = request.get_json(force=True, silent=True)

        if not data:
            return jsonify({'success': False, 'error': 'Пустой запрос'}), 400

        required = ['hall', 'eventType', 'dishes', 'date', 'startTime', 'endTime', 'name', 'phone']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Не заполнено: {field}'}), 400

        order_id = save_order(data)
        order_number = f"#DK-{datetime.now().strftime('%m%d')}-{order_id:04d}"

        print(f"✅ Заявка сохранена: {order_number}")

        return jsonify({
            'success': True,
            'orderNumber': order_number,
            'orderId': order_id
        })

    except Exception as e:
        print(f"❌ Ошибка в create_order: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    return jsonify(load_orders())

# ═══════════════════════════════════════════════════════
# ЗАПУСК
# ═══════════════════════════════════════════════════════

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Сервер ДК запущен на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
