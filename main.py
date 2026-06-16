from flask import Flask, jsonify
from flask_cors import CORS
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

app = Flask(__name__)
CORS(app)

# Подключение к Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Берём ключ из переменной окружения Railway
creds_dict = json.loads(os.environ.get('GOOGLE_CREDS'))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)

# ID твоей таблицы
SHEET_ID = "1CeSsvRuqrr0M8fv1Aef89vtwPLxrZGAnuxEkx4f08js"
sheet = gc.open_by_key(SHEET_ID).sheet1

@app.route('/')
def home():
    return jsonify({'status': 'ok', 'message': 'API работает!'})

@app.route('/api/products')
def get_products():
    try:
        products = sheet.get_all_records()
        return jsonify(products)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    try:
        products = sheet.get_all_records()
        return jsonify({
            'totalProducts': len(products),
            'totalSales': 0,
            'totalRevenue': 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
