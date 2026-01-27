import sqlite3
import requests
from flask import Flask, render_template, request, make_response

app = Flask(__name__)

HA_URL = "http://192.168.1.XX:8123/api/services/shopping_list/add_item"
HA_TOKEN = "Bearer TOKEN_ANDA"

def get_db_connection():
    conn = sqlite3.connect('pantry.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('CREATE TABLE IF NOT EXISTS items (barcode TEXT PRIMARY KEY, name TEXT, quantity INTEGER)')
    conn.commit()
    conn.close()

def get_product_name(barcode):
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

# --- ROUTE UNTUK CARIAN & TABLE ---
@app.route('/items')
def get_items():
    search_query = request.args.get('q', '')
    conn = get_db_connection()
    if search_query:
        # Cari barang berdasarkan nama (LIKE)
        items = conn.execute("SELECT * FROM items WHERE name LIKE ? ORDER BY name", ('%' + search_query + '%',)).fetchall()
    else:
        items = conn.execute("SELECT * FROM items ORDER BY name").fetchall()
    conn.close()
    return render_template('_inventory.html', items=items)

# --- ROUTE UNTUK SCANNER & UPDATE ---
@app.route('/update', methods=['POST'])
def update_item():
    barcode = request.form.get('barcode')
    action = request.form.get('action') # 'add', 'remove', 'delete'
    msg = ""

    conn = get_db_connection()
    item = conn.execute("SELECT * FROM items WHERE barcode=?", (barcode,)).fetchone()

    if not item and action == 'add':
        # Barang Baru
        name = get_product_name(barcode)
        conn.execute("INSERT INTO items VALUES (?, ?, 1)", (barcode, name))
        msg = f"Barang baru: {name} ditambah!"
    
    elif item:
        new_qty = item['quantity']
        item_name = item['name']

        if action == 'add':
            new_qty += 1
            msg = f"{item_name}: +1"
        elif action == 'remove':
            new_qty -= 1
            msg = f"{item_name}: -1"
        elif action == 'delete':
            conn.execute("DELETE FROM items WHERE barcode=?", (barcode,))
            msg = f"{item_name} dibuang dari sistem."
            new_qty = -1 # Flag untuk delete

        if new_qty == 0 and action == 'remove':
             # Logic HA (Simulasi)
             msg = f"{item_name} habis! Ditambah ke Shopping List."

        if action != 'delete':
            if new_qty < 0: new_qty = 0
            conn.execute("UPDATE items SET quantity=? WHERE barcode=?", (new_qty, barcode))

    conn.commit()
    
    # Ambil list terkini (ambil query carian semasa jika ada)
    search_query = request.args.get('q', '')
    if search_query:
        items = conn.execute("SELECT * FROM items WHERE name LIKE ? ORDER BY name", ('%' + search_query + '%',)).fetchall()
    else:
        items = conn.execute("SELECT * FROM items ORDER BY name").fetchall()
    conn.close()

    # Render table + Sertakan Toast Message (OOB Swap)
    response = make_response(render_template('_inventory.html', items=items))
    
    # Teknik HTMX OOB: Kita hantar div notifikasi sekali dengan table
    if msg:
        response.data += f'<div id="toast" hx-swap-oob="true" class="show">{msg}</div>'.encode()
    
    return response

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)