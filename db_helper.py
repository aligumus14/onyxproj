import psycopg2
from psycopg2.extras import RealDictCursor

class DatabaseHelper:
    def __init__(self):
        self.db_params = {
            "host": "localhost",
            "user": "postgres",
            "password": "silver", # <-- Şifreni kontrol et
            "dbname": "erp_ai"        # <-- Doğru DB adı olduğundan emin ol
        }

    def get_schema_info(self):
        """Veritabanı şemasını çeker."""
        schema_info = ""
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()
            
            # Tablo isimlerini al
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = cur.fetchall()
            
            for table in tables:
                table_name = table[0]
                cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}'")
                columns = cur.fetchall()
                
                schema_info += f"\nTable: {table_name}\nColumns:\n"
                for col in columns:
                    schema_info += f" - {col[0]} ({col[1]})\n"
                    
            conn.close()
            return schema_info
        except Exception as e:
            return f"Şema alınamadı: {e}"

    def execute_query(self, query):
        """
        SQL sorgusunu çalıştırır.
        Hata olursa ARTIK PRINT ETMİYOR, HATAYI FIRLATIYOR (RAISE).
        Böylece AI hatayı yakalayabilir.
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute(query)
            
            # SELECT sorgusu mu diye kontrol et (Veri dönecek mi?)
            if query.strip().upper().startswith("SELECT"):
                result = cur.fetchall()
                return result
            else:
                conn.commit() # INSERT/UPDATE ise kaydet
                return [{"status": "success", "message": "İşlem tamamlandı."}]
                
        except Exception as e:
            # BURASI DEĞİŞTİ: Hatayı yutma, yukarı fırlat!
            raise e 
            
        finally:
            if conn:
                conn.close()