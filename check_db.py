import chromadb
import os

# Veritabanına bağlan
client = chromadb.PersistentClient(path="./vector_db")
collection = client.get_or_create_collection(name="company_docs")

# Toplam belge sayısını al
count = collection.count()
print(f"📚 Toplam Vektör Parçası Sayısı: {count}")

# Belge isimlerini (Source) çekip listeleyelim
# (Hepsini çekersek terminal kilitlenir, sadece benzersiz dosya isimlerini alalım)
print("🔍 Hafızadaki Dosyalar Taranıyor...")

all_data = collection.get() # Biraz sürebilir
all_filenames = set()

if all_data["metadatas"]:
    for meta in all_data["metadatas"]:
        source = meta.get("source")
        if source:
            all_filenames.add(source)

print(f"✅ Toplam {len(all_filenames)} Farklı Dosya Bulundu.")

# Bizim aradığımız dosya var mı?
target = "INV-2025-000001" 
found = False
for fname in all_filenames:
    if target in fname:
        print(f"🎯 BULUNDU! Dosya Adı: {fname}")
        found = True
        break

if not found:
    print(f"❌ '{target}' içeren bir dosya hafızada YOK! Sorun bu.")