import psycopg2
import requests

# --- AYARLAR ---
db_params = {
    "host": "localhost",
    "user": "postgres",
    "password": "silver",  # <-- ŞİFRENİ YAZ
    "dbname": "erp_ai"
}

# Northwind SQL dosyasının ham (raw) adresi
SQL_URL = "https://raw.githubusercontent.com/pthom/northwind_psql/master/northwind.sql"

def install_northwind():
    try:
        print("⏳ Northwind SQL dosyası indiriliyor...")
        response = requests.get(SQL_URL)
        if response.status_code != 200:
            print("❌ Dosya indirilemedi! İnternet bağlantını kontrol et.")
            return
        
        sql_content = response.text
        print("✅ Dosya indirildi. Veritabanına yazılıyor...")

        conn = psycopg2.connect(**db_params)
        conn.autocommit = True
        cur = conn.cursor()

        # 1. Önce temizlik (Eski tabloları siliyoruz)
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        print("🧹 Eski tablolar temizlendi.")

        # 2. SQL'i çalıştır
        cur.execute(sql_content)
        print("🎉 Northwind tabloları başarıyla oluşturuldu!")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ HATA: {e}")

if __name__ == "__main__":
    install_northwind()