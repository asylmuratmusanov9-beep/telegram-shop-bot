from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

app = Flask(__name__)
CORS(app)

# Подключение к Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Берём JSON ключ из переменной окружения Railway
creds_dict = json.loads(os.environ.get('GOOGLE_CREDS'))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)

# ВСТАВЬ СВОЙ ID ТАБЛИЦЫ
SHEET_ID = "1CeSsvRuqrr0M8fv1Aef89vtwPLxrZGAnuxEkx4f08js"
sheet = gc.open_by_key(SHEET_ID).sheet1

@app.route('/api/products', methods=['GET'])
def get_products():
    """Получить все товары"""
    try:
        products = sheet.get_all_records()
        return jsonify(products)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products', methods=['POST'])
def add_product():
    """Добавить товар (только для админа)"""
    try:
        data = request.json
        products = sheet.get_all_records()
        new_id = len(products) + 1
        sheet.append_row([
            new_id, 
            data.get('name', ''), 
            data.get('category', ''), 
            data.get('price', 0), 
            data.get('file_id', ''), 
            data.get('preview_url', '')
        ])
        return jsonify({'success': True, 'id': new_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Удалить товар (только для админа)"""
    try:
        products = sheet.get_all_records()
        for i, p in enumerate(products, start=2):
            if p.get('id') == product_id:
                sheet.delete_rows(i)
                return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Product not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Статистика магазина"""
    try:
        products = sheet.get_all_records()
        return jsonify({
            'totalProducts': len(products),
            'totalSales': 0,
            'totalRevenue': 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return jsonify({'status': 'ok', 'message': 'API работает!'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
