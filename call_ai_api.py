import json
from db_helper import DatabaseHelper

# Eğer Onyx AI bir API üzerinden çalışıyorsa requests kütüphanesi gerekecek
# pip install requests
import requests 

class ERPAgent:
    def __init__(self):
        self.db = DatabaseHelper()
        self.schema_context = self.db.get_schema_info()
        
    def create_system_prompt(self):
        """
        AI'a kim olduğunu ve veritabanı yapısını öğreten ana prompt.
        """
        prompt = f"""
Sen uzman bir PostgreSQL Veritabanı Asistanısın. Görevin, doğal dilde sorulan soruları geçerli SQL sorgularına çevirmektir.

KURALLAR:
1. Sadece ve sadece SQL kodu üret. Açıklama yapma, "İşte kodunuz" gibi giriş cümleleri kurma.
2. SQL kodunu markdown formatında (```sql ... ```) içine alma, düz metin olarak ver.
3. Aşağıdaki veritabanı şemasını kullan. Başka tablo uydurma.
4. Sorguların PostgreSQL uyumlu olsun.

VERİTABANI ŞEMASI:
{self.schema_context}
"""
        return prompt

    def call_ai_api(self, user_question):
        """
        Burasi Onyx AI (veya kullandığın LLM) ile konuşan fonksiyondur.
        Şu an örnek olarak Ollama/OpenAI benzeri bir yapı var.
        """
        system_prompt = self.create_system_prompt()
        full_prompt = f"{system_prompt}\n\nKULLANICI SORUSU: {user_question}\nSQL:"

        print("🤖 AI Düşünüyor... (Prompt Hazırlandı)")
        
        # --- BURASI SENİN ONYX BAĞLANTIN OLACAK ---
        # ÖRNEK: Eğer lokalde bir model çalışıyorsa (Ollama vb.)
        # Eğer bir API Key varsa buraya ekleyeceğiz.
        
        # Şimdilik simüle edelim veya senin API kodunu buraya yazalım.
        # Eğer "mock" (sahte) bir cevapla denemek istersen alttaki satırı aç:
        # return "SELECT count(*) FROM employees;" 
        
        # GERÇEK BAĞLANTI İÇİN (Örnek Ollama/Localhost):
        try:
            # Burası senin Onyx endpoint'in olmalı
            # Örnek: response = requests.post("http://localhost:11434/api/generate", json={"model": "llama3", "prompt": full_prompt, "stream": False})
            # return response.json()['response']
            
            # Şimdilik hata vermemesi için bir 'NotImplemented' uyarısı dönüyorum:
            return "MOCK_SQL_MODE: Henüz AI bağlantısı yapılmadı. Lütfen call_ai_api fonksiyonunu düzenle."
            
        except Exception as e:
            return f"AI Bağlantı Hatası: {e}"

    def ask(self, question):
        # 1. AI'dan SQL al
        generated_sql = self.call_ai_api(question)
        
        # Eğer bağlantı yoksa uyarı ver
        if "MOCK_SQL_MODE" in generated_sql:
            print(f"⚠️  UYARI: {generated_sql}")
            return
            
        print(f"📝 Üretilen SQL: {generated_sql}")
        
        # 2. SQL'i temizle (Markdown karakterleri varsa sil)
        clean_sql = generated_sql.replace("```sql", "").replace("```", "").strip()
        
        # 3. Veritabanında çalıştır
        print("🚀 Veritabanında çalıştırılıyor...")
        try:
            results = self.db.execute_query(clean_sql)
            return results
        except Exception as e:
            return f"Sorgu Hatası: {e}"

# Test
if __name__ == "__main__":
    agent = ERPAgent()
    
    soru = "Toplam kaç personelimiz var?"
    print(f"\nSoru: {soru}")
    
    # Şimdilik AI bağlı olmadığı için hata veya mock dönecek
    cevap = agent.ask(soru)
    print(f"Sonuç: {cevap}")