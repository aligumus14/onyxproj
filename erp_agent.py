# erp_agent.py
import os
import re
import requests
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from json_document_store import JsonDocumentStore

# Opsiyonel: SQL tarafın için (varsa)
try:
    from db_helper import DatabaseHelper
except Exception:
    DatabaseHelper = None


# ----------------------------- Utils -----------------------------
def _norm(s: str) -> str:
    s = (s or "").lower()
    # türkçe karakterleri parçalamadan basit normalize
    s = re.sub(r"[^\w\s\-:/\.]", " ", s, flags=re.UNICODE)
    s = re.sub(r"[\s_]+", " ", s).strip()
    return s


def _format_tr_money(value: float) -> str:
    s = f"{value:,.2f}"  # 2,191.12
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")  # 2.191,12
    return s


def _to_float(x: Any, default: float = 0.0) -> float:
    """
    TR/EN para formatlarını daha güvenli parse eder.
    Ör:
      "2.191,12 TL" -> 2191.12
      "1.234" (TR binlik) -> 1234.0
      "1234.56" -> 1234.56
    """
    if x is None:
        return default
    if isinstance(x, (int, float)):
        return float(x)

    s = str(x).strip()
    if not s:
        return default

    s = s.replace("TL", "").replace("₺", "").strip()
    s = s.replace("\u00a0", " ").replace(" ", "")

    # both separators: assume TR thousand '.' decimal ','
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        # only dot -> might be thousand sep in TR ("1.234")
        if "." in s and "," not in s:
            parts = s.split(".")
            if len(parts) > 1 and len(parts[-1]) == 3:
                s = s.replace(".", "")
        s = s.replace(",", ".")

    try:
        return float(s)
    except Exception:
        return default


def _extract_doc_id(text: str) -> Optional[str]:
    """
    INV-2025-000001 / SRV-2025-000172 / HR-2024-000001
    """
    m = re.search(r"\b((INV|SRV|HR)-\d{4}-\d{6})\b", text, flags=re.IGNORECASE)
    if m:
        return m.group(1).upper()

    # eski esnek format (INV-2025-1 gibi)
    m2 = re.search(r"\b((INV|SRV|HR)-\d{4}-\d+)\b", text, flags=re.IGNORECASE)
    return m2.group(1).upper() if m2 else None


TR_MONTHS = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "mayis": 5,
    "haziran": 6, "temmuz": 7, "ağustos": 8, "agustos": 8, "eylül": 9, "eylul": 9,
    "ekim": 10, "kasım": 11, "kasim": 11, "aralık": 12, "aralik": 12
}


def _detect_year_month(text: str) -> Optional[Tuple[int, int]]:
    """
    "2025 ekim", "ekim 2025", "2025-10" gibi yakalar.
    """
    t = _norm(text)

    # YYYY-MM
    m = re.search(r"\b(20\d{2})\s*[\-\/\.]\s*(0?[1-9]|1[0-2])\b", t)
    if m:
        return int(m.group(1)), int(m.group(2))

    # month name + year
    y = re.search(r"\b(20\d{2})\b", t)
    year = int(y.group(1)) if y else None
    if not year:
        return None

    for k, mo in TR_MONTHS.items():
        if re.search(rf"\b{k}\b", t):
            return year, mo

    return None


def _month_range(year: int, month: int) -> Tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


# ----------------------------- ERPAgent -----------------------------
class ERPAgent:
    """
    UI tarafında zaten 'SQL'e sor' / 'Belgeye sor' ayrımı var:
      - ask_sql(...) => PostgreSQL
      - query_knowledge_base(...) => JSON belgeler
    """

    def __init__(self):
        # SQL
        self.db = DatabaseHelper() if DatabaseHelper else None
        self.schema_context = self.db.get_schema_info() if self.db else ""

        # JSON docs
        self.doc_store = JsonDocumentStore(json_dir=os.getenv("JSON_DOCS_DIR", "./json_docs"))

        # LLM (sadece fallback / serbest metin durumlarında)
        self.model_name = os.getenv("OLLAMA_MODEL", "llama3")
        self.api_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

        # Debug / davranış bayrakları
        self.show_candidates = os.getenv("SHOW_CANDIDATES", "0") == "1"
        self.use_llm_fallback = os.getenv("USE_LLM_FALLBACK", "1") == "1"

        # Güven eşikleri
        self.min_best_score = float(os.getenv("RAG_MIN_BEST_SCORE", "0.35"))
        self.ambiguity_gap = float(os.getenv("RAG_AMBIGUITY_GAP", "0.15"))

        # Çoklu belge cevaplama (özellikle servis raporları)
        self.multi_on_ambiguity = os.getenv("RAG_MULTI_ON_AMBIGUITY", "1") == "1"
        self.multi_max_docs = int(os.getenv("RAG_MULTI_MAX_DOCS", "5"))

    # -------------------- LLM Helpers --------------------
    def call_ai_api(self, prompt: str, temp: float = 0.1) -> str:
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temp},
        }
        try:
            r = requests.post(self.api_url, json=payload, timeout=120)
            r.raise_for_status()
            return r.json().get("response", "").strip()
        except Exception as e:
            return f"API Hatası: {e}"

    # -------------------- SQL --------------------
    def create_sql_system_prompt(self) -> str:
        return f"""
Sen PostgreSQL uzmanı kıdemli bir veri mühendisisin.
Görevin: Soruları, aşağıda verilen ŞEMAYA %100 SADIK KALARAK SQL sorgusuna çevirmektir.

KURALLAR:
1) Tablo/sütun isimleri snake_case olmalı.
2) Sadece SQL döndür (markdown yok).
3) Sorgu sonuna LIMIT 20 ekle.
4) Metin aramalarında ILIKE kullan.

ŞEMA:
{self.schema_context}
""".strip()

    def clean_sql_output(self, text: str) -> str:
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                if "select" in part.lower():
                    text = part.replace("sql", "").strip()
                    break
        start = text.lower().find("select")
        end = text.rfind(";")
        if start != -1 and end != -1:
            return text[start:end + 1]
        if start != -1:
            return text[start:]
        return text.strip()

    def ask_sql(self, user_question: str):
        if not self.db:
            return {"error": "DatabaseHelper bulunamadı / SQL mod kapalı."}

        max_retries = 3
        last_error = None
        last_sql = None
        system_prompt = self.create_sql_system_prompt()

        for attempt in range(max_retries):
            if attempt == 0:
                full_prompt = f"{system_prompt}\n\nSORU: {user_question}\nSQL:"
            else:
                full_prompt = f"""
{system_prompt}

ÖNCEKİ DENEME HATALI.
SORU: {user_question}
HATALI SQL: {last_sql}
HATA: {last_error}

Sadece düzeltilmiş SQL ver.
SQL:
""".strip()

            raw = self.call_ai_api(full_prompt, temp=0.1)
            sql = self.clean_sql_output(raw)
            last_sql = sql

            try:
                return self.db.execute_query(sql)
            except Exception as e:
                last_error = str(e)

        return {"error": "AI 3 denemede SQL üretemedi.", "last_error": last_error, "last_sql": last_sql}

    # -------------------- DOC: JsonDocumentStore Adapters --------------------
    def _doc_exists(self, doc_id: str) -> bool:
        doc_id = doc_id.upper()
        for name in ["exists", "has_doc", "doc_exists"]:
            if hasattr(self.doc_store, name):
                return bool(getattr(self.doc_store, name)(doc_id))
        try:
            self._load_doc(doc_id)
            return True
        except Exception:
            return False

    def _load_doc(self, doc_id: str) -> Dict[str, Any]:
        doc_id = doc_id.upper()
        for name in ["load_doc", "get_doc", "read_doc"]:
            if hasattr(self.doc_store, name):
                return getattr(self.doc_store, name)(doc_id)
        raise AttributeError("JsonDocumentStore: load_doc/get_doc/read_doc bulunamadı.")

    def _find_candidates(
        self,
        question: str,
        doc_type: Optional[str],
        top_k: int = 5,
        year_month: Optional[Tuple[int, int]] = None,
        vendor: Optional[str] = None,
        machine: Optional[str] = None,
        restrict_doc_ids: Optional[List[str]] = None,
    ):
        for name in ["find_candidates", "search_candidates", "candidates"]:
            if hasattr(self.doc_store, name):
                return getattr(self.doc_store, name)(
                    question,
                    doc_type=doc_type,
                    top_k=top_k,
                    year_month=year_month,
                    vendor=vendor,
                    machine=machine,
                    restrict_doc_ids=restrict_doc_ids,
                )
        raise AttributeError("JsonDocumentStore: find_candidates/search_candidates yok.")

    def _top_invoice_by_month(self, year: int, month: int) -> Optional[Dict[str, Any]]:
        if hasattr(self.doc_store, "top_invoice_by_month"):
            return self.doc_store.top_invoice_by_month(year, month)
        if hasattr(self.doc_store, "max_invoice_by_total"):
            start, end = _month_range(year, month)
            return self.doc_store.max_invoice_by_total(start, end)
        return None

    # -------------------- Deterministik Cevaplayıcılar --------------------
    def _invoice_product_hint(self, invoice: Dict[str, Any], question: str) -> Optional[str]:
        """
        Soru içinde geçen ürün adını bulur (lines[].name üzerinden).
        - Önce store.detect_product (global vocab) ile normalize ürün yakala
        - Sonra bu invoice içindeki gerçek satır adına map et
        - Fallback: eski yöntem
        """
        # 1) store bazlı (daha güçlü)
        try:
            p_norm = self.doc_store.detect_product(question) if hasattr(self.doc_store, "detect_product") else None
        except Exception:
            p_norm = None

        if p_norm:
            for ln in invoice.get("lines", []) or []:
                if _norm(ln.get("name", "")) == _norm(p_norm):
                    return ln.get("name")
            # contains / partial match
            for ln in invoice.get("lines", []) or []:
                nn = _norm(ln.get("name", ""))
                if p_norm in nn or nn in p_norm:
                    return ln.get("name")

        # 2) legacy (invoice içinden)
        qn = _norm(question)
        names = sorted({(ln.get("name") or "") for ln in invoice.get("lines", []) if ln.get("name")})
        hits = [n for n in names if _norm(n) and _norm(n) in qn]
        if hits:
            return max(hits, key=len)

        # hafif fallback: token çakışması
        q_tokens = set(qn.split())
        for n in names:
            nt = _norm(n)
            if not nt:
                continue
            if any(tok in q_tokens for tok in nt.split()):
                return n
        return None

    def _sum_product_total(self, lines: List[Dict[str, Any]], product_name: str) -> Tuple[int, float]:
        """
        Aynı ürün birden çok satırda geçebilir → satır sayısı + toplam tutar.
        Daha toleranslı eşleşme:
          - exact norm match
          - contains match (PDF kırılmaları / ek açıklamalar için)
        """
        cnt = 0
        total = 0.0

        pn = _norm(product_name)
        for ln in lines:
            ln_name = ln.get("name", "")
            ln_n = _norm(ln_name)

            match = (ln_n == pn) or (pn and pn in ln_n) or (ln_n and ln_n in pn)
            if match:
                cnt += 1
                total += _to_float(ln.get("net_total", ln.get("total", ln.get("line_total", 0.0))))
        return cnt, total

    def _best_line_by_total(self, lines: List[Dict[str, Any]]) -> Optional[Tuple[Dict[str, Any], float]]:
        best_ln = None
        best_val = -1.0
        for ln in lines:
            v = _to_float(ln.get("net_total", ln.get("total", ln.get("line_total", 0.0))))
            if v > best_val:
                best_val = v
                best_ln = ln
        if best_ln is None:
            return None
        return best_ln, best_val

    def _answer_invoice_deterministic(self, doc: Dict[str, Any], question: str) -> str:
        qn = _norm(question)
        doc_id = doc.get("doc_id", "Bilinmeyen")

        subtotal = _to_float(doc.get("subtotal"))
        vat_total = _to_float(doc.get("vat_total"))
        grand_total = _to_float(doc.get("grand_total"))
        vendor = doc.get("vendor")
        dt = doc.get("date")
        lines: List[Dict[str, Any]] = doc.get("lines", []) or []

        # 1) Ürün bazlı toplam
        product_hint = self._invoice_product_hint(doc, question)
        asks_money = ("toplam" in qn) or ("tutar" in qn) or ("kaç tl" in qn) or ("ne kadar" in qn) or ("kaç" in qn and product_hint)
        if product_hint and asks_money:
            cnt, total = self._sum_product_total(lines, product_hint)
            if cnt == 0:
                # daha açıklayıcı hata
                return f"{doc_id} belgesinde '{product_hint}' ürünü satırları bulunamadı (PDF/JSON satır ayrımı farklı olabilir)."
            return f"{doc_id} belgesinde '{product_hint}' için {cnt} satır bulundu. Toplam tutar: {_format_tr_money(total)} TL."

        # 2) Alan soruları
        if "genel toplam" in qn:
            return f"{doc_id} belgesinin Genel Toplamı: {_format_tr_money(grand_total)} TL."
        if ("kdv" in qn and "toplam" in qn) or ("kdv toplam" in qn):
            return f"{doc_id} belgesinin KDV Toplamı: {_format_tr_money(vat_total)} TL."
        if "ara toplam" in qn:
            return f"{doc_id} belgesinin Ara Toplamı: {_format_tr_money(subtotal)} TL."
        if "tedarik" in qn or "satıcı" in qn or "vendor" in qn:
            return f"{doc_id} belgesinin tedarikçisi: {vendor}."
        if "tarih" in qn or "ne zaman" in qn:
            return f"{doc_id} belgesinin tarihi: {dt}."
        if "kalem say" in qn or "kaç kalem" in qn or ("satır" in qn and "kaç" in qn):
            return f"{doc_id} belgesindeki kalem (satır) sayısı: {len(lines)}."

        # 3) En yüksek tutarlı kalem
        if ("en yüksek" in qn or "en buyuk" in qn) and ("ürün" in qn or "urun" in qn or "kalem" in qn or "tutar" in qn):
            best = self._best_line_by_total(lines)
            if best:
                ln, v = best
                return f"{doc_id} belgesinde en yüksek tutarlı kalem: '{ln.get('name')}' — {_format_tr_money(v)} TL (net)."

        # 4) Default kısa özet
        return (
            f"{doc_id} — Tarih: {dt} | Tedarikçi: {vendor}\n"
            f"Ara Toplam: {_format_tr_money(subtotal)} TL | KDV: {_format_tr_money(vat_total)} TL | Genel Toplam: {_format_tr_money(grand_total)} TL\n"
            f"Kalem sayısı: {len(lines)}"
        )

    def _answer_service_deterministic(self, doc: Dict[str, Any], question: str) -> str:
        qn = _norm(question)
        doc_id = doc.get("doc_id", "Bilinmeyen")
        fault = doc.get("fault_description") or ""
        actions = doc.get("actions") or []
        machine = doc.get("machine") or ""
        dt = doc.get("date") or ""

        wants_fault = ("arıza nedeni" in qn) or (("arıza" in qn or "ariza" in qn) and ("neden" in qn or "sebep" in qn))
        wants_actions = ("yapılan işlemler" in qn) or ("yapilan islemler" in qn) or ("işlemler" in qn) or ("islemler" in qn)

        if wants_fault and wants_actions:
            lines = "\n".join([f"- {a}" for a in actions]) if actions else "- (Kayıt yok)"
            return f"{doc_id} ({machine}, {dt})\nArıza nedeni: {fault}\nYapılan işlemler:\n{lines}"

        if wants_fault:
            return f"{doc_id} servis raporunda arıza nedeni: {fault}"

        if wants_actions:
            if not actions:
                return f"{doc_id} servis raporunda yapılan işlemler kaydı bulunamadı."
            lines = "\n".join([f"- {a}" for a in actions])
            return f"{doc_id} servis raporunda yapılan işlemler:\n{lines}"

        return f"{doc_id} ({machine}, {dt}) — Durum: {doc.get('status')} | Öncelik: {doc.get('priority')}"

    def _answer_hr_deterministic(self, doc: Dict[str, Any], doc_id: str) -> str:
        r = doc.get("recipient", {}) or {}
        return (
            f"{doc_id} — {doc.get('subject')}\n"
            f"Tarih: {doc.get('date')} | Tür: {doc.get('hr_kind')} | Alıcı: {r.get('name')} ({r.get('department')})"
        )

    # -------------------- LLM fallback (seçilmiş belge üzerinden) --------------------
    def _llm_fallback(self, question: str, doc: Dict[str, Any]) -> str:
        raw = (doc.get("raw_text") or "")[:3500]
        meta = {
            "doc_id": doc.get("doc_id"),
            "doc_type": doc.get("doc_type"),
            "date": doc.get("date"),
            "vendor": doc.get("vendor"),
            "machine": doc.get("machine"),
            "subject": doc.get("subject"),
        }

        prompt = f"""
Sen kurumsal ERP belge asistanısın.
SADECE aşağıdaki JSON meta + raw_text'e dayanarak cevap ver. Uydurma yok.

META (JSON):
{meta}

RAW_TEXT:
{raw}

SORU: {question}

KURALLAR:
- Belirsizse "belgede bu bilgi yok" de.
- Türkçe, net, kısa.

CEVAP:
""".strip()
        return self.call_ai_api(prompt, temp=0.0)

    # -------------------- Selection helpers --------------------
    def _wants_all_documents(self, question: str) -> bool:
        qn = _norm(question)
        return ("hepsi" in qn) or ("tümü" in qn) or ("tumu" in qn) or ("her bir" in qn) or ("her biri" in qn) or ("ayrı ayrı" in qn) or ("ayri ayri" in qn)

    def _wants_service_actions(self, question: str) -> bool:
        qn = _norm(question)
        return ("yapılan işlemler" in qn) or ("yapilan islemler" in qn) or ("işlemler" in qn) or ("islemler" in qn) or ("yapılanlar" in qn) or ("yapilanlar" in qn)

    def _wants_service_fault(self, question: str) -> bool:
        qn = _norm(question)
        return ("arıza nedeni" in qn) or ("ariza nedeni" in qn) or (("arıza" in qn or "ariza" in qn) and ("neden" in qn or "sebep" in qn))

    def _multi_answer_service_reports(self, question: str, rows: List[Dict[str, Any]]) -> str:
        # rows: index satırları (doc_id/doc_type/date/machine vs.)
        out: List[str] = []
        for r in rows[: max(1, self.multi_max_docs)]:
            doc_id = (r.get("doc_id") or "").upper()
            if not doc_id:
                continue
            try:
                doc = self._load_doc(doc_id)
            except Exception:
                continue
            out.append(self._answer_service_deterministic(doc, question))

        if not out:
            return "İlgili servis raporları bulundu ancak içerikleri okunamadı."

        header = "Birden fazla servis raporu eşleşti. Aşağıda her rapor için sonuçları (en uygun olandan düşüğe) listeliyorum:"
        return header + "\n\n" + "\n\n".join(out)

    def _guess_doc_type_smart(self, question: str) -> Optional[str]:
        """
        Sadece keyword'e değil, entity sinyallerine de bakar.
        """
        qn = _norm(question)

        # Strong keywords
        if "servis" in qn or "arıza" in qn or "ariza" in qn or "bakım raporu" in qn or "bakim raporu" in qn:
            return "service_report"
        if "ik" in qn or "insan kaynak" in qn or "uyarı" in qn or "uyari" in qn or "terfi" in qn:
            return "hr_letter"
        if "fatura" in qn or "fiş" in qn or "fis" in qn or "kdv" in qn or "ara toplam" in qn or "genel toplam" in qn:
            return "invoice"

        # Entity-based hints
        try:
            if hasattr(self.doc_store, "detect_machine") and self.doc_store.detect_machine(question):
                return "service_report"
            if hasattr(self.doc_store, "detect_product") and self.doc_store.detect_product(question):
                return "invoice"
            if hasattr(self.doc_store, "detect_vendor") and self.doc_store.detect_vendor(question):
                return "invoice"
        except Exception:
            pass

        return None

    # -------------------- Main: Belgeye Sor --------------------
    
    # -------------------- Main: Belgeye Sor (Structured) --------------------
    def query_knowledge_base(self, user_question: str) -> str:
        """Backward compatible: sadece cevap metnini döndürür."""
        res = self.query_knowledge_base_structured(user_question)
        return res.get("answer", "")

    def query_knowledge_base_structured(self, user_question: str) -> Dict[str, Any]:
        """
        Structured dönüş:
          {
            "answer": str,
            "mode": "id" | "vendor_max" | "retrieval" | "need_id" | "not_found" | "error",
            "selected_doc_id": str | None,
            "candidates": [ { ... } ]   # UI'da göstermek için
          }

        Not: UI'da "baktığı belgeleri göster" isteği için candidates doldurulur.
        """
        qn = _norm(user_question)

        def cand_row(score: Optional[float], row: Dict[str, Any]) -> Dict[str, Any]:
            d = {
                "doc_id": row.get("doc_id"),
                "doc_type": row.get("doc_type"),
                "date": row.get("date"),
                "vendor": row.get("vendor"),
                "machine": row.get("machine"),
            }
            if score is not None:
                d["score"] = float(score)
            # invoice toplamı index'te varsa taşı
            if row.get("doc_type") == "invoice" and row.get("grand_total") is not None:
                d["grand_total"] = float(_to_float(row.get("grand_total")))
            return d

        # 1) ID varsa: deterministik
        doc_id = _extract_doc_id(user_question)
        if doc_id and self._doc_exists(doc_id):
            doc = self._load_doc(doc_id)
            dt = doc.get("doc_type")

            if dt == "invoice":
                return {
                    "mode": "id",
                    "selected_doc_id": doc_id,
                    "candidates": [{"doc_id": doc_id, "doc_type": "invoice"}],
                    "answer": self._answer_invoice_deterministic(doc, user_question),
                }
            if dt == "service_report":
                return {
                    "mode": "id",
                    "selected_doc_id": doc_id,
                    "candidates": [{"doc_id": doc_id, "doc_type": "service_report"}],
                    "answer": self._answer_service_deterministic(doc, user_question),
                }
            if dt == "hr_letter":
                return {
                    "mode": "id",
                    "selected_doc_id": doc_id,
                    "candidates": [{"doc_id": doc_id, "doc_type": "hr_letter"}],
                    "answer": self._answer_hr_deterministic(doc, doc_id),
                }

            if self.use_llm_fallback:
                return {
                    "mode": "id",
                    "selected_doc_id": doc_id,
                    "candidates": [{"doc_id": doc_id, "doc_type": dt}],
                    "answer": self._llm_fallback(user_question, doc),
                }
            return {
                "mode": "id",
                "selected_doc_id": doc_id,
                "candidates": [{"doc_id": doc_id, "doc_type": dt}],
                "answer": f"{doc_id} belgesi bulundu ama doc_type tanınmadı.",
            }

        # 2) ID YOK: constraints + intent
        year_month = _detect_year_month(user_question)

        # vendor/machine/product sinyalleri
        vendor = None
        machine = None
        restrict_ids = None
        try:
            vendor = self.doc_store.detect_vendor(user_question) if hasattr(self.doc_store, "detect_vendor") else None
            machine = self.doc_store.detect_machine(user_question) if hasattr(self.doc_store, "detect_machine") else None

            # Product -> invoice id kısıtı
            if hasattr(self.doc_store, "detect_product") and hasattr(self.doc_store, "invoice_ids_for_product"):
                p = self.doc_store.detect_product(user_question)
                if p:
                    restrict_ids = self.doc_store.invoice_ids_for_product(p)
        except Exception:
            pass

        # 2A) ÖZEL: "X tedarikçisinin en yüksek genel toplamlı faturası hangisi"
        is_max = ("en yüksek" in qn or "en buyuk" in qn) and ("fatura" in qn or "invoice" in qn)
        is_total = ("genel toplam" in qn) or ("toplam" in qn and ("genel" in qn or "tutar" in qn))
        is_vendorish = ("tedarik" in qn) or (vendor is not None)

        if is_max and is_total and is_vendorish and vendor:
            # index üzerinden vendor faturalarını sıralayıp max'ı seç
            if hasattr(self.doc_store, "top_invoices_for_vendor"):
                pack = self.doc_store.top_invoices_for_vendor(vendor, n=10, year_month=year_month)
                top_rows = pack.get("top", []) or []
                candidates = [cand_row(None, r) for r in top_rows]
                if not top_rows:
                    return {
                        "mode": "not_found",
                        "selected_doc_id": None,
                        "candidates": [],
                        "answer": f"'{vendor}' tedarikçisine ait fatura bulunamadı.",
                    }

                best_row = top_rows[0]
                best_id = best_row.get("doc_id")
                try:
                    best_doc = self._load_doc(best_id)
                except Exception:
                    best_doc = None

                gt = _to_float(best_row.get("grand_total"))
                dt = best_row.get("date")

                answer = (
                    f"{vendor} tedarikçisinin en yüksek Genel Toplamlı faturası: {best_id} (Tarih: {dt})\n"
                    f"Genel Toplam: {_format_tr_money(gt)} TL."
                )

                # UI'da gösterim için kısa liste (top 5)
                preview = top_rows[:5]
                if preview:
                    lines = [f"- {r.get('doc_id')} | {r.get('date')} | {_format_tr_money(_to_float(r.get('grand_total')))} TL"
                             for r in preview]
                    answer += "\n\nİncelediğim (en yüksekten düşüğe) ilk 5 fatura:\n" + "\n".join(lines)
                    count_all = int(pack.get("count", 0))
                    if count_all > len(preview):
                        answer += f"\n… (toplam {count_all} fatura tarandı)"

                # İstersen detaylı invoice cevabını da ekle
                if best_doc is not None and "detay" in qn:
                    answer += "\n\n" + self._answer_invoice_deterministic(best_doc, user_question)

                return {
                    "mode": "vendor_max",
                    "selected_doc_id": best_id,
                    "candidates": candidates,
                    "answer": answer,
                }

        # 2B) Analitik: "2025 Ekim ayındaki en yüksek tutarlı faturayı getir" (vendor yoksa)
        if "fatura" in qn and ("en yüksek" in qn or "en buyuk" in qn) and ("tutar" in qn or "toplam" in qn):
            ym = year_month
            if ym:
                y, m = ym
                best_row = self._top_invoice_by_month(y, m)
                if best_row and best_row.get("doc_id"):
                    best_doc = self._load_doc(best_row["doc_id"])
                    answer = self._answer_invoice_deterministic(best_doc, user_question)
                    return {
                        "mode": "retrieval",
                        "selected_doc_id": best_row["doc_id"],
                        "candidates": [cand_row(None, best_row)],
                        "answer": answer,
                    }

        # 2C) Genel aday bulma (retrieval)
        doc_type = self._guess_doc_type_smart(user_question)
        if restrict_ids and doc_type is None:
            doc_type = "invoice"

        try:
            cands = self._find_candidates(
                user_question,
                doc_type=doc_type,
                top_k=5,
                year_month=year_month,
                vendor=vendor,
                machine=machine,
                restrict_doc_ids=restrict_ids,
            )
        except Exception as e:
            return {"mode": "error", "selected_doc_id": None, "candidates": [], "answer": f"Belge indeksi aday bulma sırasında hata: {e}"}

        # düşük güven / boş -> doc_type'sız dene
        if (not cands) or (isinstance(cands[0], (tuple, list)) and float(cands[0][0]) <= 0.05 and doc_type is not None):
            try:
                cands2 = self._find_candidates(
                    user_question,
                    doc_type=None,
                    top_k=5,
                    year_month=year_month,
                    vendor=vendor,
                    machine=machine,
                    restrict_doc_ids=restrict_ids,
                )
                if cands2:
                    cands = cands2
            except Exception:
                pass

        if not cands:
            return {"mode": "not_found", "selected_doc_id": None, "candidates": [], "answer": "Belge indeksinde bu soruya uygun kayıt bulunamadı."}

        # normalize [(score,row)]
        norm_cands: List[Tuple[float, Dict[str, Any]]] = []
        if isinstance(cands[0], (tuple, list)) and len(cands[0]) >= 2:
            for item in cands:
                try:
                    score = float(item[0])
                    row = item[1]
                    if isinstance(row, dict) and row.get("doc_id"):
                        norm_cands.append((score, row))
                except Exception:
                    continue
        elif isinstance(cands[0], dict):
            for row in cands:
                if row.get("doc_id"):
                    norm_cands.append((0.0, row))

        if not norm_cands:
            return {"mode": "error", "selected_doc_id": None, "candidates": [], "answer": "Aday liste formatı beklenenden farklı; doc_id bulunamadı."}

        norm_cands.sort(key=lambda x: x[0], reverse=True)
        best_score, best_row = norm_cands[0]
        second_score = norm_cands[1][0] if len(norm_cands) > 1 else -999.0
        best_id = (best_row.get("doc_id") or "").upper()

        candidates_out = [cand_row(s, r) for s, r in norm_cands[:5]]

        # belirsizlik guard
        force_all = self._wants_all_documents(user_question)

        is_ambiguous = (best_score < self.min_best_score) or (len(norm_cands) > 1 and (best_score - second_score) < self.ambiguity_gap)
        if is_ambiguous or force_all:
            # Servis raporlarında (özellikle makine + işlemler soruları) ID istemeden çoklu cevap ver.
            any_service = any((r.get("doc_type") == "service_report") for _, r in norm_cands[: self.multi_max_docs])
            wants_service = (doc_type == "service_report") or any_service
            wants_actions = self._wants_service_actions(user_question)
            wants_fault = self._wants_service_fault(user_question)

            if self.multi_on_ambiguity and wants_service and (wants_actions or wants_fault):
                rows = [r for _, r in norm_cands[: self.multi_max_docs] if r.get("doc_id")]
                answer = self._multi_answer_service_reports(user_question, rows)

                if self.show_candidates:
                    answer += "\n\n[ADAYLAR]\n" + "\n".join(
                        [f"- {r.get('doc_id')} | score={s:.2f} | type={r.get('doc_type')} | date={r.get('date')} | vendor={r.get('vendor')} | machine={r.get('machine')}"
                         for s, r in norm_cands[: self.multi_max_docs]]
                    )

                return {"mode": "multi", "selected_doc_id": None, "candidates": candidates_out, "answer": answer}

            # default: ID iste
            ids = ", ".join([r.get("doc_id") for _, r in norm_cands[:5] if r.get("doc_id")])
            answer = (
                "Sorunuz birden fazla belgeyle eşleşiyor ve tek bir belgeyi güvenle seçemiyorum.\n"
                f"Lütfen şu adaylardan belge ID'sini yazarak tekrar sorun: {ids}"
            )
            if self.show_candidates:
                answer += "\n\n[ADAYLAR]\n" + "\n".join(
                    [f"- {r.get('doc_id')} | score={s:.2f} | type={r.get('doc_type')} | date={r.get('date')} | vendor={r.get('vendor')} | machine={r.get('machine')}"
                     for s, r in norm_cands[:5]]
                )
            return {"mode": "need_id", "selected_doc_id": None, "candidates": candidates_out, "answer": answer}

        # seçilen belgeyi cevapla
        doc = self._load_doc(best_id)
        if doc.get("doc_type") == "invoice":
            answer = self._answer_invoice_deterministic(doc, user_question)
        elif doc.get("doc_type") == "service_report":
            answer = self._answer_service_deterministic(doc, user_question)
        elif doc.get("doc_type") == "hr_letter":
            answer = self._answer_hr_deterministic(doc, best_id)
        elif self.use_llm_fallback:
            answer = self._llm_fallback(user_question, doc)
        else:
            answer = f"{best_id} belgesi seçildi ama doc_type tanınmadı."

        # Eğer servis raporu seçildiyse ve başka güçlü adaylar da varsa, diğer raporları da listele.
        if doc.get("doc_type") == "service_report" and len(norm_cands) > 1 and not self._wants_all_documents(user_question):
            others = []
            for s, r in norm_cands[1: self.multi_max_docs]:
                oid = r.get("doc_id")
                if not oid:
                    continue
                others.append(f"- {oid} | {r.get('date')} | score={s:.2f}")
            if others:
                answer += "\n\nDiğer ilgili servis raporları:\n" + "\n".join(others)

        if self.show_candidates:
            answer += "\n\n[ADAYLAR]\n" + "\n".join(
                [f"- {r.get('doc_id')} | score={s:.2f} | type={r.get('doc_type')} | date={r.get('date')} | vendor={r.get('vendor')} | machine={r.get('machine')}"
                 for s, r in norm_cands[:3]]
            )

        return {
            "mode": "retrieval",
            "selected_doc_id": best_id,
            "candidates": candidates_out,
            "answer": answer,
        }
