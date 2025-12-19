import os
import time
import pdfplumber  # <--- YENİ KÜTÜPHANE
from document_store import DocumentStore
from tqdm import tqdm

PDF_FOLDER_PATH = "./pdfs" 

def bulk_ingest():
    store = DocumentStore()
    
    if not os.path.exists(PDF_FOLDER_PATH):
        print(f"❌ '{PDF_FOLDER_PATH}' klasörü bulunamadı!")
        return

    files = [f for f in os.listdir(PDF_FOLDER_PATH) if f.lower().endswith('.pdf')]
    total_files = len(files)
    
    if total_files == 0:
        print(f"⚠️ '{PDF_FOLDER_PATH}' klasörü boş!")
        return

    print(f"🚀 Akıllı Tablo Okuma Modu (pdfplumber) Başlıyor! Dosya Sayısı: {total_files}")
    
    start_time = time.time()
    success_count = 0
    error_count = 0

    for filename in tqdm(files, desc="Yükleniyor"):
        try:
            file_path = os.path.join(PDF_FOLDER_PATH, filename)
            text = ""
            
            # --- YENİ OKUMA MANTIĞI ---
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # layout=True: Harflerin fiziksel konumuna göre boşluk bırakır.
                    # Tabloları excel gibi hizalı çıkarır.
                    extracted = page.extract_text(layout=True)
                    if extracted:
                        text += extracted + "\n"
            # --------------------------

            if not text.strip():
                error_count += 1
                continue

            store.add_document(text, filename)
            success_count += 1

        except Exception as e:
            # print(f"Hata: {e}")
            error_count += 1

    end_time = time.time()
    print("\n" + "="*40)
    print(f"🏁 İŞLEM TAMAMLANDI!")
    print(f"✅ Başarılı: {success_count}")
    print(f"❌ Başarısız: {error_count}")
    print(f"⏱️ Geçen Süre: {end_time - start_time:.2f} saniye")
    print("="*40)

if __name__ == "__main__":
    bulk_ingest()