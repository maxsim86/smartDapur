import sqlite3
import requests
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

# --- KONFIGURASI HOME ASSISTANT ---
HA_URL = "http://192.168.1.XX:8123/api/services/shopping_list/add_item"
HA_TOKEN = "Bearer YOUR_LONG_LIVED_ACCESS_TOKEN_HERE"

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('pantry.db')
    c = conn.cursor()
    # Table barang: barcode, nama, quantity
    c.execute('''CREATE TABLE IF NOT EXISTS items 
                 (barcode TEXT PRIMARY KEY, name TEXT, quantity INTEGER)''')
    conn.commit()
    conn.close()

# --- FUNGSI CARI NAMA BARANG (OPEN FOOD FACTS) ---
def get_product_name(barcode):
    # API percuma & open source untuk data makanan
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        if data['status'] == 1:
            return data['product'].get('product_name', 'Produk Tidak Dikenali')
    except:
        pass
    return "Produk Baru"

# --- FUNGSI HANTAR KE HOME ASSISTANT ---
def add_to_ha_shopping_list(item_name):
    headers = {
        "Authorization": HA_TOKEN,
        "content-type": "application/json",
    }
    data = {"name": f"Beli: {item_name}"}
    try:
        requests.post(HA_URL, headers=headers, json=data)
        print(f"Dihantar ke HA: {item_name}")
    except Exception as e:
        print(f"Gagal connect ke HA: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    conn = sqlite3.connect('pantry.db')
    c = conn.cursor()

    if request.method == 'POST':
        # Input dari USB Scanner masuk ke sini
        barcode = request.form['barcode']
        action = request.form['action'] # 'add' atau 'remove'

        # Cek kalau barang dah ada
        c.execute("SELECT * FROM items WHERE barcode=?", (barcode,))
        item = c.fetchone()

        if item:
            new_qty = item[2] + 1 if action == 'add' else item[2] - 1
            if new_qty < 0: new_qty = 0
            
            # Update quantity
            c.execute("UPDATE items SET quantity=? WHERE barcode=?", (new_qty, barcode))
            
            # LOGIC BIJAK: Kalau stok jadi 0, hantar ke HA
            if new_qty == 0 and action == 'remove':
                add_to_ha_shopping_list(item[1])
                
        else:
            # Barang baru, cari nama dari internet
            if action == 'add':
                name = get_product_name(barcode)
                c.execute("INSERT INTO items VALUES (?, ?, 1)", (barcode, name))

        conn.commit()
        return redirect('/')

    # Papar semua barang
    c.execute("SELECT * FROM items")
    items = c.fetchall()
    conn.close()
    return render_template('index.html', items=items)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)