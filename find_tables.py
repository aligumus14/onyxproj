import psycopg2

# Scriptin kullandığı ayarlar
db_params = {
    "host": "localhost",
    "user": "postgres",
    "password": "silver", # <-- Şifreni Yaz
    "dbname": "erp_ai"       # Kodda kullandığımız isim bu
}

try:
    conn = psycopg2.connect(**db_params)
    cur = conn.cursor()
    
    # Mevcut veritabanındaki tabloları listele
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    tables = cur.fetchall()
    
    print(f"📡 Bağlanılan Veritabanı: {db_params['dbname']}")
    print(f"📊 Bulunan Tablo Sayısı: {len(tables)}")
    
    if len(tables) > 0:
        print("✅ TABLOLAR BURADA! PgAdmin'de bu isimli veritabanını bulmalısın.")
        print("Bulunan bazı tablolar:", [t[0] for t in tables[:14]])
    else:
        print("❌ Bu veritabanı boş.")
        
    conn.close()

except psycopg2.OperationalError:
    print(f"❌ HATA: '{db_params['dbname']}' adında bir veritabanı yok!")