import json
import requests
from db_helper import DatabaseHelper
from document_store import DocumentStore  # RAG (Belge Hafızası) için gerekli

class ERPAgent:
    def __init__(self):
        # Veritabanı ve Belge Deposu bağlantıları
        self.db = DatabaseHelper()
        self.doc_store = DocumentStore()
        
        # Veritabanı şemasını başlangıçta hafızaya al
        self.schema_context = self.db.get_schema_info()
        
        # AI Ayarları (Local Llama 3)
        self.model_name = "llama3" 
        self.api_url = "http://localhost:11434/api/generate"

    # --- 1. SQL ÜRETİMİ İÇİN PROMPT ---
    def create_sql_system_prompt(self):
        return f"""
Sen PostgreSQL uzmanı kıdemli bir veri mühendisisin.
Görevin: Soruları, aşağıda verilen ŞEMAYA %100 SADIK KALARAK SQL sorgusuna çevirmektir.

### KESİN KURALLAR (BUNLARA UYMAZSAN SİSTEM ÇÖKER) ###
1. Tablo ve Sütun isimleri PostgreSQL'de KÜÇÜK HARF ve ALT ÇİZGİLİDİR (snake_case).
   - Yanlış: OrderId, OrderDate, ProductId, Employees
   - Doğru: order_id, order_date, product_id, employees
2. Asla "Orders", "Employees" gibi büyük harfle başlayan tablo isimleri kullanma.
3. SADECE SQL kodu döndür. Markdown (```sql) veya açıklama ekleme.
4. Veri yoğunluğunu önlemek için sorgu sonuna LIMIT 20 ekle.
5. Metin aramalarında büyük/küçük harf sorunu için ILIKE kullan.

### VERİTABANI ŞEMASI ###
{self.schema_context}
"""

    # --- 2. YARDIMCI METODLAR ---
    def clean_sql_output(self, text):
        """AI'ın gevezeliklerini temizler, saf SQL bırakır."""
        # Markdown temizliği
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                if "select" in part.lower():
                    text = part.replace("sql", "").strip()
                    break
        
        # Sadece SQL kısmını cımbızla çek
        start = text.lower().find("select")
        end = text.rfind(";")
        
        if start != -1 and end != -1:
            return text[start : end + 1]
        elif start != -1:
             return text[start:] # Noktalı virgül unutulmuşsa
             
        return text.strip()

    def call_ai_api(self, prompt, temp=0.1):
        """Ollama'ya istek atan genel fonksiyon."""
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temp} # 0.1: Tutarlı (SQL), 0.7: Yaratıcı (Rapor)
        }
        try:
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception as e:
            return f"API Hatası: {e}"

    # --- 3. ANA ÖZELLİKLER ---

    def ask_sql(self, user_question):
        """
        Kendi Hatasını Düzelten (Self-Correction) SQL Motoru.
        Soru -> SQL -> Hata -> AI Düzelt -> SQL -> Başarı
        """
        max_retries = 3
        last_error = None
        last_sql = None
        
        system_prompt = self.create_sql_system_prompt()

        print(f"\n🧠 SQL Analizi Başlıyor: {user_question}")

        for attempt in range(max_retries):
            # Prompt Hazırlama
            if attempt == 0:
                full_prompt = f"{system_prompt}\n\nSORU: {user_question}\nSQL:"
            else:
                # Hata durumunda AI'a fırça atıp düzelttiriyoruz
                print(f"⚠️ Hata yakalandı (Deneme {attempt+1}/{max_retries}). AI düzeltiyor...")
                full_prompt = f"""
{system_prompt}

ÖNCEKİ DENEMENDE HATA YAPTIN!
SORU: {user_question}
HATALI SQL: {last_sql}
HATA MESAJI: {last_error}

GÖREV: Hata mesajını oku ve SQL'i düzelt. Sadece düzeltilmiş SQL'i ver.
SQL:
"""
            # AI'dan Yanıt Al
            raw_response = self.call_ai_api(full_prompt, temp=0.1)
            clean_sql = self.clean_sql_output(raw_response)
            last_sql = clean_sql

            # Çalıştırmayı Dene
            try:
                print(f"🚀 SQL Çalıştırılıyor: {clean_sql}")
                results = self.db.execute_query(clean_sql)
                return results # Başarılıysa sonucu döndür
            except Exception as e:
                last_error = str(e) # Hatayı sakla, döngü devam etsin
        
        print("❌ AI 3 denemede de başaramadı.")
        return None

    def analyze_data(self, question, data):
        """
        SQL sonuçlarını alır ve Profesyonel Yönetici Raporu yazar.
        PDF çıktısına uygun formatta (Başlıklar halinde) üretir.
        """
        # Veri çoksa AI'ı boğmamak için ilk 20 satırı veriyoruz
        data_preview = str(data[:20]) 
        
        prompt = f"""
Sen Kurumsal Bir İş Zekası (BI) Uzmanısın. Aşağıdaki veriyi analiz et.

KULLANICI SORUSU: {question}
VERİ TABLOSU: {data_preview}

GÖREV:
Bu veriyi bir PDF raporuna basılacak şekilde profesyonelce yorumla.
Lütfen aşağıdaki formatı KESİNLİKLE kullan:

### 1. YÖNETİCİ ÖZETİ
(Buraya genel durumu özetleyen 2-3 cümle yaz)

### 2. DETAYLI BULGULAR
(Buraya verideki trendleri, en yüksek/düşük değerleri madde madde analiz et)

### 3. STRATEJİK ÖNERİLER
(Buraya şirket yönetimi için aksiyon önerileri yaz)

DİL: Türkçe, Resmi ve Kurumsal.
"""
        print("📊 Veri Analiz Ediliyor...")
        return self.call_ai_api(prompt, temp=0.6)

    # --- 4. RAG / BELGE ÖZELLİKLERİ ---

    def ingest_document(self, text, filename):
        """Yüklenen PDF'i parçalayıp Vektör Veritabanına (ChromaDB) kaydeder."""
        print(f"📥 Belge İşleniyor: {filename}")
        self.doc_store.add_document(text, filename)
        # Ayrıca belgenin kısa bir özetini döndürelim
        summary_prompt = f"Bu metni 1 cümleyle özetle: {text[:1000]}"
        return self.call_ai_api(summary_prompt, temp=0.5)

    def query_knowledge_base(self, user_question):
        import re
        
        # 1. Fatura No/ID Yakala
        invoice_match = re.search(r'(INV-\d{4}-\d+)', user_question)
        target_filename = None
        
        if invoice_match:
            target_inv = invoice_match.group(1)
            print(f"🎯 Hedef ID: {target_inv}")
            
            # Dedektifi çağır (Artık log basacak)
            target_filename = self.doc_store.find_filename_by_text(target_inv)
            
            if not target_filename:
                print(f"⚠️ Uyarı: '{target_inv}' için kesin dosya bulunamadı. Genel arama yapılıyor...")
                # BURASI ÖNEMLİ: Bulamasa bile işlemi durdurmuyoruz, target_filename None kalıyor.
        
        # 2. Aramayı Yap
        # Dosya bulunduysa filtrele, bulunmadıysa genel havuzda ara
        context_chunks = self.doc_store.search_document(
            user_question, 
            n_results=20, # Pencere geniş
            filter_filename=target_filename 
        )
        
        if not context_chunks:
            return "Veritabanı sorgusu boş sonuç döndü."

        context_text = "\n---\n".join(context_chunks)

        # 3. AI Prompt (Sıkı Kurallar)
        prompt = f"""
Sen Uzman Bir Muhasebe Asistanısın.
Görevin, aşağıdaki OCR (Optik Karakter Tanıma) ile okunmuş fatura verilerini analiz etmektir.

VERİ:
{context_text}

SORU: {user_question}

KURALLAR:
1. Veriler TABLO formatındadır. Sütunların hizasına dikkat et.
2. Genellikle format şöyledir: [Ürün Adı] [Miktar] [Birim Fiyat] [Toplam]
3. Satırları birbirine karıştırma. Ürün adının hemen sağındaki sayı genellikle Miktardır.
4. "Dana Kıyma" için birden fazla satır varsa, hepsini bul ve topla.
5. Sadece metinde KESİN olarak yazan sayıları kullan.

CEVAP:
"""
        print(f"🧠 AI Analize Gönderiliyor...")
        return self.call_ai_api(prompt, temp=0.0)