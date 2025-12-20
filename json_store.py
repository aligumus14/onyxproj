import os, json, re
from typing import Optional, Dict, Any, List

INV_RE = re.compile(r"\b(INV-\d{4}-\d{6})\b")
SRV_RE = re.compile(r"\b(SRV-\d{4}-\d{6})\b")
HR_RE  = re.compile(r"\b(HR-\d{4}-\d{6})\b")

def safe_load_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

class JsonDocumentStore:
    """
    PDF->JSON dönüşümü sonrası:
    - ./json_docs/INV-2025-000001.json gibi dosyaları okur
    - index.jsonl varsa hızlı tarama yapar
    """
    def __init__(self, json_dir: str = "./json_docs"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.json_dir = os.path.abspath(os.getenv("JSON_DOCS_DIR", os.path.join(base_dir, json_dir)))
        self.index_path = os.path.join(self.json_dir, "index.jsonl")

        if not os.path.exists(self.json_dir):
            raise FileNotFoundError(f"json_dir bulunamadı: {self.json_dir}")

    def find_doc_id_in_question(self, q: str) -> Optional[str]:
        for r in (INV_RE, SRV_RE, HR_RE):
            m = r.search(q)
            if m:
                return m.group(1)
        return None

    def load_by_doc_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        p = os.path.join(self.json_dir, f"{doc_id}.json")
        if not os.path.exists(p):
            return None
        return safe_load_json(p)

    def search_index_simple(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Basit lexical arama (index.jsonl üstünden).
        İstersen sonra BM25 ekleriz; şimdilik debug + MVP için yeter.
        """
        keyword_l = keyword.lower().strip()
        hits = []
        if not os.path.exists(self.index_path):
            return hits

        with open(self.index_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except:
                    continue
                blob = json.dumps(obj, ensure_ascii=False).lower()
                if keyword_l in blob:
                    hits.append(obj)
                    if len(hits) >= limit:
                        break
        return hits
