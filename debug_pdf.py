import os
from pypdf import PdfReader

# PDF klasörünün yolu
PDF_FOLDER = "./pdfs"
TARGET_ID = "INV-2025-000001"

def debug_pdf():
    print(f"🔍 '{PDF_FOLDER}' klasöründeki dosyalar taranıyor...\n")
    
    files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')]
    
    found_file = None
    
    # 1. Dosya isminde ID'yi ara
    for f in files:
        if TARGET_ID in f:
            print(f"📄 Dosya İsmi Eşleşti: {f}")
            found_file = f
            break
    
    if not found_file:
        print(f"❌ '{TARGET_ID}' ismini içeren bir dosya bulunamadı!")
        print("Lütfen dosya adının doğru olduğundan emin ol.")
        # Eğer dosya adında ID yoksa, manuel olarak dosya adını buraya yazabilirsin:
        # found_file = "fatura_ornek.pdf" 
        return

    # 2. İçeriği Oku
    file_path = os.path.join(PDF_FOLDER, found_file)
    try:
        reader = PdfReader(file_path)
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"
            
        print(f"\n📖 '{found_file}' OKUNUYOR...")
        print("="*40)
        print(full_text.strip())
        print("="*40)
        
        # 3. İçerik Kontrolü
        if TARGET_ID in full_text:
            print(f"\n✅ BAŞARILI: '{TARGET_ID}' metnin içinde aynen geçiyor.")
            print("👉 Sorun Veritabanında. Çözüm: 'vector_db' klasörünü sil ve yeniden yükle.")
        else:
            print(f"\n❌ BAŞARISIZ: '{TARGET_ID}' metnin içinde BULUNAMADI.")
            print("👉 Sorun PDF Formatında. Python bu PDF'i metin olarak okuyamıyor (Resim olabilir).")
            
    except Exception as e:
        print(f"HATA: {e}")

if __name__ == "__main__":
    debug_pdf()