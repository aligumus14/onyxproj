# json_document_store.py
import os
import re
import json
import math
from typing import Any, Dict, List, Optional, Tuple, Iterable, Set


# ---------------------- Normalization ----------------------
def _norm(s: str) -> str:
    """
    Light Turkish-friendly normalize:
    - lower
    - non-word -> space (unicode aware)
    - collapse whitespace
    """
    s = (s or "").lower()
    s = re.sub(r"[\W_]+", " ", s, flags=re.UNICODE)
    return " ".join(s.split())


# A tiny TR stopword set (kept short on purpose)
_STOPWORDS: Set[str] = {
    "ve", "veya", "ile", "için", "icin", "da", "de", "mi", "mı", "mu", "mü",
    "nedir", "ne", "kaç", "kac", "hangi", "bu", "şu", "su", "o",
    "toplam", "tutar", "genel", "ara", "kdv", "fatura", "fiş", "fis",
    "servis", "rapor", "ik", "insan", "kaynak", "yazı", "yazi",
    "belge", "no", "numara", "numarası", "numarasi",
}


def _tokenize(s: str) -> List[str]:
    toks = _norm(s).split()
    # keep short tokens if they are meaningful like "tl"? but it doesn't help retrieval here
    return [t for t in toks if t and t not in _STOPWORDS]


def _safe_float(x: Any, default: float = 0.0) -> float:
    if x is None:
        return default
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s:
        return default
    # "1.586,60" -> 1586.60
    s = s.replace("TL", "").replace("₺", "").strip()
    s = s.replace("\u00a0", " ").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        # if only dot exists in TR data, it is usually thousand-sep: "1.234" -> 1234
        if "." in s and "," not in s:
            parts = s.split(".")
            if len(parts[-1]) == 3:
                s = s.replace(".", "")
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return default


class JsonDocumentStore:
    """
    JSON klasörü yapısı:
      json_docs/
        index.jsonl
        INV-2025-000001.json
        SRV-2025-000172.json
        HR-2025-0000xx.json
        ...

    index.jsonl satırları (örnek):
      {"doc_id":"INV-...","doc_type":"invoice","date":"YYYY-MM-DD","vendor":"...","grand_total":4984.21, ...}
      {"doc_id":"SRV-...","doc_type":"service_report","date":"...","machine":"...","status":"...","priority":"..."}
      {"doc_id":"HR-...","doc_type":"hr_letter","date":"...","subject":"...","hr_kind":"...","recipient_department":"..."}
    """

    def __init__(self, json_dir: str = "./json_docs"):
        self.json_dir = os.path.abspath(json_dir)
        self.index_path = os.path.join(self.json_dir, "index.jsonl")

        print(f"📁 [JsonDocumentStore] JSON_DIR: {self.json_dir}")
        print(f"📄 [JsonDocumentStore] INDEX: {self.index_path} (exists={os.path.exists(self.index_path)})")

        self.rows: List[Dict[str, Any]] = []
        self.rows_by_id: Dict[str, Dict[str, Any]] = {}

        # Lexical index
        self._doc_text: Dict[str, str] = {}
        self._doc_tokens: Dict[str, List[str]] = {}
        self._df: Dict[str, int] = {}
        self._N: int = 0
        self._avgdl: float = 1.0

        # Entity vocab (vendor/machine/subject)
        self.vendors: List[str] = []
        self.machines: List[str] = []
        self.hr_subjects: List[str] = []

        # Product index (invoice only)
        # norm_product -> set(doc_id)
        self._product_index: Optional[Dict[str, set]] = None
        self._product_vocab: Optional[List[str]] = None
        self._products_by_doc: Optional[Dict[str, Set[str]]] = None

        # Raw-text token cache for 2nd stage scoring (lazy)
        self._raw_token_cache: Dict[str, Set[str]] = {}

        self._load_index()
        self._build_lexical()

    # ---------------------- Loaders ----------------------
    def _load_index(self) -> None:
        if not os.path.exists(self.index_path):
            raise FileNotFoundError(f"index.jsonl bulunamadı: {self.index_path}")

        with open(self.index_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                doc_id = row.get("doc_id")
                if not doc_id:
                    continue
                self.rows.append(row)
                self.rows_by_id[doc_id] = row

        # build vocabs (small sets)
        vset, mset, sset = set(), set(), set()
        for r in self.rows:
            if r.get("doc_type") == "invoice" and r.get("vendor"):
                vset.add(r["vendor"])
            if r.get("doc_type") == "service_report" and r.get("machine"):
                mset.add(r["machine"])
            if r.get("doc_type") == "hr_letter" and r.get("subject"):
                sset.add(r["subject"])

        self.vendors = sorted(vset)
        self.machines = sorted(mset)
        self.hr_subjects = sorted(sset)

    def _row_text(self, r: Dict[str, Any]) -> str:
        dt = r.get("doc_type")
        if dt == "invoice":
            # NOTE: ürünler index'te yok. (2. aşama + product index ile tamamlıyoruz)
            return f"{r.get('doc_id','')} {r.get('vendor','')} {r.get('date','')} fatura invoice kdv ara toplam genel toplam"
        if dt == "service_report":
            return f"{r.get('doc_id','')} {r.get('machine','')} {r.get('status','')} {r.get('priority','')} servis service rapor ariza bakım islem"
        if dt == "hr_letter":
            return f"{r.get('doc_id','')} {r.get('subject','')} {r.get('hr_kind','')} {r.get('recipient_department','')} insan kaynak ik uyarı terfi yazı letter"
        return f"{r.get('doc_id','')} {dt or ''}"

    def _build_lexical(self) -> None:
        self._doc_text = {r["doc_id"]: self._row_text(r) for r in self.rows}
        self._doc_tokens = {doc_id: _tokenize(txt) for doc_id, txt in self._doc_text.items()}

        self._N = len(self._doc_tokens)
        if self._N == 0:
            self._avgdl = 1.0
            return

        self._avgdl = sum(len(toks) for toks in self._doc_tokens.values()) / max(1, self._N)

        df: Dict[str, int] = {}
        for _, toks in self._doc_tokens.items():
            for t in set(toks):
                df[t] = df.get(t, 0) + 1
        self._df = df

    # ---------------------- Basics ----------------------
    def exists(self, doc_id: str) -> bool:
        return doc_id in self.rows_by_id and os.path.exists(self.doc_path(doc_id))

    def doc_path(self, doc_id: str) -> str:
        return os.path.join(self.json_dir, f"{doc_id}.json")

    def load_doc(self, doc_id: str) -> Dict[str, Any]:
        p = self.doc_path(doc_id)
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    # ---------------------- Constraints extraction ----------------------
    def detect_vendor(self, question: str) -> Optional[str]:
        qn = _norm(question)
        best = None
        best_len = 0
        for v in self.vendors:
            vn = _norm(v)
            if vn and vn in qn and len(vn) > best_len:
                best = v
                best_len = len(vn)
        return best

    def detect_machine(self, question: str) -> Optional[str]:
        qn = _norm(question)
        best = None
        best_len = 0
        for m in self.machines:
            mn = _norm(m)
            if mn and mn in qn and len(mn) > best_len:
                best = m
                best_len = len(mn)
        return best

    # ---------------------- Product index (invoice) ----------------------
    def _ensure_product_index(self) -> None:
        """
        600 invoice JSON dosyasında ~20 ürün var -> bu index hızlı oluşur.
        Ayrıca doc_id -> ürün set'i de oluşturur (2. aşama skor için).
        """
        if self._product_index is not None and self._product_vocab is not None and self._products_by_doc is not None:
            return

        prod_index: Dict[str, set] = {}
        products_by_doc: Dict[str, Set[str]] = {}
        vocab_set = set()

        for fname in os.listdir(self.json_dir):
            if not fname.startswith("INV-") or not fname.endswith(".json"):
                continue
            doc_id = fname[:-5]
            try:
                doc = self.load_doc(doc_id)
            except Exception:
                continue
            for ln in doc.get("lines", []) or []:
                name = (ln.get("name") or "").strip()
                if not name:
                    continue
                pn = _norm(name)
                if not pn:
                    continue
                vocab_set.add(pn)
                prod_index.setdefault(pn, set()).add(doc_id)
                products_by_doc.setdefault(doc_id, set()).add(pn)

        self._product_index = prod_index
        self._product_vocab = sorted(vocab_set, key=len, reverse=True)
        self._products_by_doc = products_by_doc

    def detect_product(self, question: str) -> Optional[str]:
        """
        Soru içinde geçen ürün adını yakalar.
        Return: normalized product string (örn "dana kıyma")
        """
        self._ensure_product_index()
        qn = _norm(question)
        for p in self._product_vocab or []:
            if p in qn:
                return p
        # very soft fallback: token overlap (for "dana kiyma" vs "dana kıyma")
        q_tokens = set(_tokenize(question))
        best = None
        best_score = 0
        for p in (self._product_vocab or [])[:200]:  # keep it bounded
            pt = set(p.split())
            score = len(pt & q_tokens)
            if score > best_score:
                best_score = score
                best = p
        return best if best_score >= 2 else None

    def invoice_ids_for_product(self, normalized_product: str) -> List[str]:
        self._ensure_product_index()
        return sorted(list((self._product_index or {}).get(normalized_product, set())))

    # ---------------------- BM25 scoring ----------------------
    def _bm25(self, query: str, doc_id: str, k1: float = 1.5, b: float = 0.75) -> float:
        q = _tokenize(query)
        if not q:
            return 0.0
        toks = self._doc_tokens.get(doc_id, [])
        if not toks:
            return 0.0

        freq: Dict[str, int] = {}
        for t in toks:
            freq[t] = freq.get(t, 0) + 1

        dl = len(toks)
        score = 0.0

        for t in q:
            n = self._df.get(t, 0)
            if n <= 0:
                continue
            idf = math.log(1 + (self._N - n + 0.5) / (n + 0.5))
            f = freq.get(t, 0)
            denom = f + k1 * (1 - b + b * dl / max(1e-9, self._avgdl))
            if denom > 0:
                score += idf * (f * (k1 + 1) / denom)

        return float(score)

    # ---------------------- Filters ----------------------
    @staticmethod
    def _ym_from_date(date_str: str) -> Optional[Tuple[int, int]]:
        if not date_str:
            return None
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", date_str)
        if not m:
            return None
        return int(m.group(1)), int(m.group(2))

    def _iter_filtered(
        self,
        doc_type: Optional[str],
        year_month: Optional[Tuple[int, int]],
        vendor: Optional[str],
        machine: Optional[str],
        restrict_ids: Optional[set],
    ) -> Iterable[Dict[str, Any]]:
        for r in self.rows:
            if doc_type and r.get("doc_type") != doc_type:
                continue
            if restrict_ids is not None and r.get("doc_id") not in restrict_ids:
                continue
            if vendor and r.get("vendor") != vendor:
                continue
            if machine and r.get("machine") != machine:
                continue
            if year_month:
                ym = self._ym_from_date(r.get("date", ""))
                if not ym or ym != year_month:
                    continue
            yield r

    # ---------------------- 2nd stage scoring ----------------------
    def _raw_tokens_for_doc(self, doc_id: str) -> Set[str]:
        """
        Tokenize selected fields of the *actual* JSON doc.
        Lazy cache to avoid repeated disk reads.
        """
        if doc_id in self._raw_token_cache:
            return self._raw_token_cache[doc_id]

        try:
            doc = self.load_doc(doc_id)
        except Exception:
            self._raw_token_cache[doc_id] = set()
            return set()

        # Use fault/actions for service; lines for invoice; subject/body for HR; plus doc_id/vendor/machine
        dt = doc.get("doc_type")
        parts: List[str] = [doc_id]
        if doc.get("vendor"):
            parts.append(str(doc.get("vendor")))
        if doc.get("machine"):
            parts.append(str(doc.get("machine")))
        if dt == "service_report":
            parts.append(str(doc.get("fault_description") or ""))
            parts.extend([str(x) for x in (doc.get("actions") or [])])
        elif dt == "invoice":
            for ln in (doc.get("lines") or []):
                parts.append(str(ln.get("name") or ""))
        elif dt == "hr_letter":
            parts.append(str(doc.get("subject") or ""))
            parts.append(str(doc.get("body_text") or ""))

        # Keep it bounded to reduce memory/time
        joined = " ".join(parts)
        toks = set(_tokenize(joined))
        self._raw_token_cache[doc_id] = toks
        return toks

    # ---------------------- Public: candidate search ----------------------
    def find_candidates(
        self,
        question: str,
        doc_type: Optional[str] = None,
        top_k: int = 5,
        year_month: Optional[Tuple[int, int]] = None,
        vendor: Optional[str] = None,
        machine: Optional[str] = None,
        restrict_doc_ids: Optional[List[str]] = None,
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """
        Returns: [(score, row), ...] sorted desc

        Fixes:
        - score=0 tie issues: add entity boosts + optional 2nd stage scoring from actual JSON
        - invoice product questions: auto-restrict + boost by product match
        - service fault questions: 2nd stage scoring uses fault/actions fields
        """
        # Auto entity detection if caller didn't supply
        detected_vendor = vendor or self.detect_vendor(question)
        detected_machine = machine or self.detect_machine(question)

        detected_product = None
        restrict_ids = set(restrict_doc_ids) if restrict_doc_ids else None
        if (doc_type == "invoice" or doc_type is None):
            detected_product = self.detect_product(question)
            if detected_product:
                ids = set(self.invoice_ids_for_product(detected_product))
                restrict_ids = ids if restrict_ids is None else (restrict_ids & ids)

        # If doc_type is unknown and we detected machine strongly, bias to service_report at least for scoring/filters
        # (caller can still run multi-pass searches)
        scored: List[Tuple[float, Dict[str, Any]]] = []
        pool: List[Dict[str, Any]] = list(self._iter_filtered(doc_type, year_month, detected_vendor, detected_machine, restrict_ids))

        # If pool is empty because too aggressive filters, relax step-by-step
        if not pool and restrict_ids is not None:
            pool = list(self._iter_filtered(doc_type, year_month, detected_vendor, detected_machine, None))
            restrict_ids = None
        if not pool and (detected_vendor or detected_machine):
            pool = list(self._iter_filtered(doc_type, year_month, None, None, restrict_ids))

        # 1st stage: BM25 over index text + boosts
        for r in pool:
            doc_id = r["doc_id"]
            s = self._bm25(question, doc_id)

            # entity boosts (strong signals)
            if detected_vendor and r.get("vendor") == detected_vendor:
                s += 1.0
            if detected_machine and r.get("machine") == detected_machine:
                s += 1.2
            if year_month:
                ym = self._ym_from_date(r.get("date", ""))
                if ym == year_month:
                    s += 0.6

            # invoice product boost
            if detected_product and r.get("doc_type") == "invoice":
                self._ensure_product_index()
                if doc_id in (self._products_by_doc or {}) and detected_product in (self._products_by_doc or {}).get(doc_id, set()):
                    s += 1.6

            # tiny deterministic tiebreak by date
            d = r.get("date", "")
            if re.match(r"^\d{4}-\d{2}-\d{2}$", d):
                s += float(d.replace("-", "")) * 1e-9

            scored.append((float(s), r))

        scored.sort(key=lambda x: x[0], reverse=True)

        # If still low-confidence / ambiguous, run 2nd stage scoring from actual JSON docs
        best = scored[0][0] if scored else 0.0
        second = scored[1][0] if len(scored) > 1 else 0.0
        q_tokens = set(_tokenize(question))
        # if query carries tokens that are not present in the index row_text, BM25 becomes uninformative
        has_novel = any(t not in self._df for t in q_tokens)
        is_tie = len(scored) > 1 and abs(best - second) < 0.05

        if pool and (best <= 0.05 or is_tie or has_novel):
            rescored: List[Tuple[float, Dict[str, Any]]] = []
            # bound the scan
            max_scan = int(os.getenv("RAG_SECOND_STAGE_MAX", "250"))
            for s0, r in scored[:max_scan]:
                doc_id = r["doc_id"]
                doc_toks = self._raw_tokens_for_doc(doc_id)
                overlap = len(q_tokens & doc_toks)
                # overlap is a strong clue; keep base score for deterministic stability
                s = s0 + overlap * 0.35
                rescored.append((float(s), r))
            rescored.sort(key=lambda x: x[0], reverse=True)
            scored = rescored

        return scored[:top_k]

    # ---------------------- Invoice helpers ----------------------
    def top_invoice_by_month(self, year: int, month: int, vendor: Optional[str] = None) -> Optional[Dict[str, Any]]:
        best = None
        best_total = -1.0
        for r in self._iter_filtered("invoice", (year, month), vendor, None, None):
            gt = _safe_float(r.get("grand_total"))
            if gt > best_total:
                best_total = gt
                best = r
        return best

    def latest_doc(
        self,
        doc_type: str,
        vendor: Optional[str] = None,
        machine: Optional[str] = None,
        year_month: Optional[Tuple[int, int]] = None,
    ) -> Optional[Dict[str, Any]]:
        best = None
        best_date = ""
        for r in self._iter_filtered(doc_type, year_month, vendor, machine, None):
            d = r.get("date", "")
            if d and d > best_date:
                best_date = d
                best = r
        return best

    # ---------------------- Invoice aggregation helpers ----------------------
    def top_invoices_for_vendor(
        self,
        vendor: str,
        n: int = 5,
        year_month: Optional[Tuple[int, int]] = None,
    ) -> Dict[str, Any]:
        """ 
        Vendor'a ait faturaları index.jsonl üzerinden grand_total'a göre sıralar.

        Return:
          {
            "vendor": vendor,
            "year_month": (y,m) | None,
            "count": toplam_fatura_sayisi,
            "top": [ {row}, ... ]  # row: index.jsonl satırı
          }
        """
        rows = list(self._iter_filtered("invoice", year_month, vendor, None, None))
        rows.sort(key=lambda r: _safe_float(r.get("grand_total")), reverse=True)
        return {
            "vendor": vendor,
            "year_month": year_month,
            "count": len(rows),
            "top": rows[: max(1, int(n))],
        }

    def top_invoice(
        self,
        vendor: Optional[str] = None,
        year_month: Optional[Tuple[int, int]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Vendor yoksa tüm faturalar arasında, varsa vendor faturaları arasında max grand_total."""
        best = None
        best_total = -1.0
        for r in self._iter_filtered("invoice", year_month, vendor, None, None):
            gt = _safe_float(r.get("grand_total"))
            if gt > best_total:
                best_total = gt
                best = r
        return best
