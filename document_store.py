import chromadb
import uuid

class DocumentStore:
    def __init__(self):
        # Verileri 'vector_db' klasörüne kaydeder, program kapansa da silinmez.
        self.client = chromadb.PersistentClient(path="./vector_db")
        self.collection = self.client.get_or_create_collection(name="company_docs")

    def add_document(self, text, filename):
        """
        Belgeyi parçalara ayırır (Overlap ekleyerek kelime bölünmesini önler).
        """
        chunk_size = 1000
        overlap = 200  # <--- YENİ: Parçalar birbirinin üstüne 200 karakter binsin
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Eğer chunk çok kısaysa (son parça) ve boşsa ekleme
            if len(chunk.strip()) > 10:
                chunks.append(chunk)
            
            # Bir sonraki parça, 200 karakter geriden başlasın
            start += (chunk_size - overlap)
        
        # Her parça için ID ve metadata oluştur
        ids = [f"{filename}_{i}" for i in range(len(chunks))]
        metadatas = [{"source": filename} for _ in chunks]

        if len(chunks) > 0:
            # print(f"💾 {filename} -> {len(chunks)} parça olarak kaydediliyor.") 
            self.collection.add(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )

    def search_document(self, query, n_results=5, filter_filename=None):
        """
        filter_filename: Eğer belirtilirse SADECE o dosya içinde arama yapar.
        """
        # Filtre ayarı (ChromaDB 'where' parametresi kullanır)
        where_clause = {"source": filter_filename} if filter_filename else None

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_clause # <--- Bu satır büyüyü yapan yer
        )
        
        # Liste olarak döndür
        if results["documents"] and results["documents"][0]:
            return results["documents"][0]
        return []
    
    # --- YENİ EKLENECEK FONKSİYON ---
    def find_filename_by_text(self, text_query):
        print(f"\n🕵️ DEBUG: '{text_query}' için Süper Esnek Arama Başlıyor...")
        
        # Arama Penceresini 300'e çıkarıyoruz (Garanti olsun)
        results = self.collection.query(
            query_texts=[text_query],
            n_results=300 
        )
        
        if not results["documents"] or not results["documents"][0]:
            print("❌ Vektör sonuç dönmedi.")
            return None

        # 1. Sorguyu "Çıplak" Hale Getir (Boşluk yok, tire yok, küçük harf)
        # Örn: "INV-2025-001" -> "inv2025001"
        normalized_query = text_query.lower().replace(" ", "").replace("-", "").replace("_", "").strip()
        print(f"🔹 Aranan (Normalize): {normalized_query}")

        for i, doc_text in enumerate(results["documents"][0]):
            filename = results["metadatas"][0][i].get("source")
            
            # 2. Hedef Metinleri de "Çıplak" Hale Getir
            normalized_filename = filename.lower().replace(" ", "").replace("-", "").replace("_", "")
            normalized_text = doc_text.lower().replace(" ", "").replace("-", "").replace("_", "").replace("\n", "")

            # A) Dosya İsminde Ara
            if normalized_query in normalized_filename:
                print(f"✅ EŞLEŞME (Dosya Adı): {filename}")
                return filename

            # B) İçerikte Ara
            if normalized_query in normalized_text:
                print(f"✅ EŞLEŞME (İçerik): {filename}")
                # Hatta ne bulduğunu da görelim:
                start_index = normalized_text.find(normalized_query)
                print(f"   -> Bulunan kısım: ...{normalized_text[start_index:start_index+20]}...")
                return filename
        
        print("❌ HATA: 300 aday tarandı, esnek aramada bile bulunamadı.")
        # Debug için ilk adayın dosya ismini yazdıralım ki ne görüyor anlayalım
        if len(results["metadatas"][0]) > 0:
            print(f"   -> İlk aday dosya: {results['metadatas'][0][0].get('source')}")
            
        return None