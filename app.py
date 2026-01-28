import sqlite3
import requests
import json
from flask import Flask, render_template, request, make_response

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('pantry.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_product_name(barcode):
    # (Kod sama seperti sebelum ini...)
    try:
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        r = requests.get(url, timeout=2)
        data = r.json()
        if data.get('status') == 1:
            return data['product'].get('product_name', 'Produk Tidak Dikenali')
    except:
        pass
    return "Produk Baru"

@app.route('/')
def index():
    conn = get_db_connection()
    items = conn.execute("SELECT * FROM items ORDER BY name").fetchall()
    conn.close()
    return render_template('base.html', items=items)

@app.route('/items')
def get_items():
    # (Kod sama seperti sebelum ini...)
    search_query = request.args.get('q', '')
    conn = get_db_connection()
    if search_query:
        items = conn.execute("SELECT * FROM items WHERE name LIKE ? ORDER BY name", ('%' + search_query + '%',)).fetchall()
    else:
        items = conn.execute("SELECT * FROM items ORDER BY name").fetchall()
    conn.close()
    return render_template('_inventory.html', items=items)

@app.route('/update', methods=['POST'])
def update_item():
    barcode = request.form.get('barcode')
    action = request.form.get('action')
    msg = "Tiada perubahan"
    msg_type = "info" # info, success, warning

    conn = get_db_connection()
    item = conn.execute("SELECT * FROM items WHERE barcode=?", (barcode,)).fetchone()

    # --- LOGIC DATABASE ---
    if not item and action == 'add':
        name = get_product_name(barcode)
        conn.execute("INSERT INTO items VALUES (?, ?, 1)", (barcode, name))
        msg = f"Barang baru: {name}"
        msg_type = "success"
    
    elif item:
        new_qty = item['quantity']
        if action == 'add':
            new_qty += 1
            msg = f"{item['name']}: +1"
            msg_type = "success"
        elif action == 'remove':
            new_qty -= 1
            msg = f"{item['name']}: -1"
            msg_type = "warning"
        elif action == 'delete':
            conn.execute("DELETE FROM items WHERE barcode=?", (barcode,))
            msg = f"{item['name']} dipadam."
            msg_type = "error"
            new_qty = -1

        if action != 'delete':
            if new_qty < 0: new_qty = 0
            conn.execute("UPDATE items SET quantity=? WHERE barcode=?", (new_qty, barcode))

    conn.commit()
    
    # Ambil list terkini
    items = conn.execute("SELECT * FROM items ORDER BY name").fetchall()
    conn.close()

    # --- RENDER TABLE ---
    response = make_response(render_template('_inventory.html', items=items))
    
    # --- TEKNIK PRO: 'HX-Trigger' ---
    # Kita hantar JSON signal ke AlpineJS
    trigger_data = {
        "showToast": {
            "message": msg,
            "type": msg_type
        }
    }
    response.headers['HX-Trigger'] = json.dumps(trigger_data)
    
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)