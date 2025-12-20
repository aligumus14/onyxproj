from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from erp_agent import ERPAgent
from fpdf import FPDF
import uvicorn
import io
from pypdf import PdfReader 
import re
from fastapi import HTTPException

from decimal import Decimal
import math

app = FastAPI(title="ERP AI Agent API")

# CORS Ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ajanı başlat
agent = ERPAgent()

# --- Modeller ---
class QueryRequest(BaseModel):
    question: str

class ReportRequest(BaseModel):
    summary: str
    question: str

# --- Endpointler ---

def _json_safe(v):
    """Decimal/NaN/Inf gibi şeyleri JSON'a güvenli çevir."""
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    return v

def _normalize_rows(rows):
    """rows: list[dict] varsayımıyla tüm değerleri JSON-safe yap."""
    if rows is None:
        return []
    if isinstance(rows, dict):
        # bazı agentler tek dict döndürebilir -> listeye al
        rows = [rows]
    if not isinstance(rows, list):
        # fallback: string vs
        return rows

    out = []
    for r in rows:
        if isinstance(r, dict):
            out.append({k: _json_safe(v) for k, v in r.items()})
        else:
            out.append(_json_safe(r))
    return out

def _round_money_like_fields(rows, digits=2):
    """
    Kolon adında total/sales/amount/price gibi kelimeler varsa float değerleri 2 haneye yuvarla.
    (Bu, float kuyruğu problemini pratikte bitirir.)
    """
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        return rows

    money_keys = ("total", "sales", "amount", "revenue", "price", "cost", "sum", "grand")
    for r in rows:
        for k, v in list(r.items()):
            lk = str(k).lower()
            if any(mk in lk for mk in money_keys):
                if isinstance(v, (int, float)) and v is not None:
                    r[k] = round(float(v), digits)
    return rows

def _infer_meta(rows):
    """
    Basit meta: row_count, columns, numeric_columns, money_hint
    """
    meta = {
        "row_count": 0,
        "columns": [],
        "numeric_columns": [],
        "money_hint": False,
    }
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        meta["row_count"] = len(rows)
        cols = list(rows[0].keys())
        meta["columns"] = cols

        numeric_cols = []
        for c in cols:
            v = rows[0].get(c)
            if isinstance(v, (int, float)) and v is not None:
                numeric_cols.append(c)
        meta["numeric_columns"] = numeric_cols

        money_keys = ("total", "sales", "amount", "revenue", "price", "cost", "grand")
        meta["money_hint"] = any(any(mk in str(c).lower() for mk in money_keys) for c in cols)

    return meta


@app.post("/ask")
def ask_ai(request: QueryRequest):
    """SQL Soruları için - iyileştirilmiş"""
    try:
        q = (request.question or "").strip()
        print(f"📩 SQL Sorusu: {q}")

        # 1) SQL çalıştır (agent içinde SQL üretilip koşuyor)
        raw_result = agent.ask_sql(q)

        if raw_result is None:
            return {"success": False, "message": "SQL üretilemedi."}

        # 2) Agent bazı projelerde {'sql':..., 'rows':...} döndürebiliyor
        sql_text = None
        rows = raw_result
        if isinstance(raw_result, dict) and ("rows" in raw_result or "data" in raw_result):
            rows = raw_result.get("rows") if "rows" in raw_result else raw_result.get("data")
            sql_text = raw_result.get("sql") or raw_result.get("query")

        # 3) Agent'in son SQL'ini loglamak için (varsa)
        if sql_text is None:
            sql_text = getattr(agent, "last_sql", None) or getattr(agent, "last_query", None)

        if sql_text:
            print(f"🧾 SQL: {sql_text}")

        # 4) JSON-safe + para benzeri kolonları yuvarla
        rows = _normalize_rows(rows)
        rows = _round_money_like_fields(rows, digits=2)

        # 5) Özet rapor (opsiyonel)
        if hasattr(agent, "analyze_data"):
            summary_report = agent.analyze_data(q, rows)
        else:
            summary_report = ""

        # 6) Meta (UI sağlamlaşsın)
        meta = _infer_meta(rows)
        meta["sql"] = sql_text  # UI debug için istersen gösterme, log için de yeterli

        return {
            "success": True,
            "data": rows,
            "summary": summary_report,
            "meta": meta
        }

    except Exception as e:
        print(f"❌ HATA /ask: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask-doc")
def ask_document(request: QueryRequest):
    """Belge (PDF/JSON) Soruları için (RAG)"""
    try:
        print(f"📩 Belge Sorusu: {request.question}")

        # Structured dönüş: UI'da 'baktığı belgeleri' gösterebilmek için
        result = agent.query_knowledge_base_structured(request.question)

        return {
            "success": True,
            "answer": result.get("answer", ""),
            "mode": result.get("mode"),
            "selected_doc_id": result.get("selected_doc_id"),
            "candidates": result.get("candidates", []),
        }
    except Exception as e:
        print(f"HATA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """PDF Yükleme ve Hafızaya Kaydetme"""
    try:
        content = ""
        filename = file.filename
        
        # PDF Okuma
        if filename.endswith(".pdf"):
            pdf_bytes = await file.read()
            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    content += text + "\n"
        else:
            content_bytes = await file.read()
            content = content_bytes.decode("utf-8")
            
        if not content.strip():
            return {"success": False, "message": "Belge boş."}

        # Not: Bu proje sürümünde ingest_document opsiyonel olabilir
        if hasattr(agent, "ingest_document"):
            summary = agent.ingest_document(content, filename)
        else:
            summary = "(ingest_document fonksiyonu tanımlı değil)"

        return {
            "success": True,
            "filename": filename,
            "summary": summary
        }

    except Exception as e:
        print(f"UPLOAD HATASI: {e}")
        return {"success": False, "message": str(e)}

# PDF İndirme (Türkçe Karakter Destekli)
def clean_text(text):
    replacements = {
        "ş": "s", "Ş": "S", "ğ": "g", "Ğ": "G", "ı": "i", "İ": "I",
        "ç": "c", "Ç": "C", "ö": "o", "Ö": "O", "ü": "u", "Ü": "U"
    }
    for search, replace in replacements.items():
        text = text.replace(search, replace)
    return text

@app.post("/download-pdf")
def generate_pdf(request: ReportRequest):
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Tasarım: Lacivert Başlık
        pdf.set_fill_color(44, 62, 80)
        pdf.rect(0, 0, 210, 40, 'F')
        
        pdf.set_font("Arial", "B", 24)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 25, "ONYX AI RAPORU", 0, 1, 'C')
        
        pdf.ln(20)
        
        # Soru
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(0, 10, txt=f" KONU: {clean_text(request.question)}", ln=True, fill=True)
        pdf.ln(10)

        # İçerik
        pdf.set_font("Arial", size=11)
        raw_text = clean_text(request.summary)
        lines = raw_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            if line.startswith("###") or (line.isupper() and len(line) < 50):
                clean_line = line.replace("#", "").strip()
                pdf.ln(5)
                pdf.set_font("Arial", "B", 14)
                pdf.set_text_color(41, 128, 185) # Mavi
                pdf.cell(0, 10, clean_line, 0, 1)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", size=11)
            else:
                pdf.multi_cell(0, 7, txt=line)
                
        # Footer
        pdf.set_y(-20)
        pdf.set_font("Arial", "I", 8)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 10, "Onyx AI Kurumsal Raporlama Sistemi", 0, 0, 'C')

        pdf_output = pdf.output(dest='S').encode('latin-1')
        
        return Response(
            content=pdf_output, 
            media_type="application/pdf", 
            headers={"Content-Disposition": "attachment; filename=rapor.pdf"}
        )

    except Exception as e:
        print(f"PDF Hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/document/{doc_id}")
def get_document(doc_id: str):
    doc_id = (doc_id or "").strip().upper()

    if not re.match(r"^(INV|SRV|HR)-\d{4}-\d{6}$", doc_id):
        raise HTTPException(status_code=400, detail="Invalid document id format")

    try:
        store = getattr(agent, "doc_store", None) or getattr(agent, "document_store", None) or getattr(agent, "store", None)
        if store is None:
            raise AttributeError("ERPAgent üzerinde doc_store/document_store/store bulunamadı.")

        if hasattr(store, "load_doc"):
            doc = store.load_doc(doc_id)
        elif hasattr(store, "get_doc"):
            doc = store.get_doc(doc_id)
        elif hasattr(store, "read_doc"):
            doc = store.read_doc(doc_id)
        else:
            raise AttributeError("Doc store üzerinde load_doc/get_doc/read_doc yok.")

        return {"success": True, "doc_id": doc_id, "doc_type": doc.get("doc_type"), "document": doc}

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)