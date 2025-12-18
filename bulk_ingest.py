import os
import time
from pypdf import PdfReader
from document_store import DocumentStore
from tqdm import tqdm

# ARTIK SENİN BELİRTTİĞİN KLASÖRE BAKIYOR
PDF_FOLDER_PATH = "./pdfs" 

def bulk_ingest():
    store = DocumentStore()
    
    # Klasör yoksa uyar
    if not os.path.exists(PDF_FOLDER_PATH):
        print(f"❌ HATA: '{PDF_FOLDER_PATH}' klasörü bulunamadı!")
        print("📂 Lütfen proje klasöründe 'pdfs' adında bir klasör olduğundan emin ol.")
        return

    # Sadece .pdf uzantılı dosyaları bul
    files = [f for f in os.listdir(PDF_FOLDER_PATH) if f.lower().endswith('.pdf')]
    total_files = len(files)
    
    # Klasör boşsa uyar
    if total_files == 0:
        print(f"⚠️ UYARI: '{PDF_FOLDER_PATH}' klasörünün içi boş!")
        print("📂 Lütfen PDF dosyalarını bu klasöre atıp tekrar dene.")
        return

    print(f"🚀 Toplu Yükleme Başlıyor! Hedef Klasör: {PDF_FOLDER_PATH}")
    print(f"📄 Toplam Dosya: {total_files}")
    
    start_time = time.time()
    success_count = 0
    error_count = 0

    # İlerleme çubuğu ile yükleme
    for filename in tqdm(files, desc="Yükleniyor"):
        try:
            file_path = os.path.join(PDF_FOLDER_PATH, filename)
            
            text = ""
            reader = PdfReader(file_path)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            
            if not text.strip():
                error_count += 1
                continue

            store.add_document(text, filename)
            success_count += 1

        except Exception as e:
            error_count += 1

    end_time = time.time()
    duration = end_time - start_time

    print("\n" + "="*40)
    print(f"🏁 İŞLEM TAMAMLANDI!")
    print(f"✅ Başarılı: {success_count}")
    print(f"❌ Başarısız: {error_count}")
    
    if total_files > 0:
        print(f"⏱️ Geçen Süre: {duration:.2f} saniye")
        print(f"📊 Ortalama Hız: {duration/total_files:.2f} sn/dosya")
    print("="*40)

if __name__ == "__main__":
    bulk_ingest()