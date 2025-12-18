from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from erp_agent import ERPAgent
from fpdf import FPDF
import uvicorn
import io
from pypdf import PdfReader 

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

@app.post("/ask")
def ask_ai(request: QueryRequest):
    """SQL Soruları için"""
    try:
        print(f"📩 SQL Sorusu: {request.question}")
        
        # 1. SQL Çalıştır
        raw_result = agent.ask_sql(request.question)
        
        if raw_result is None:
            return {"success": False, "message": "SQL üretilemedi."}
        
        # 2. Rapor Yaz
        summary_report = agent.analyze_data(request.question, raw_result)
            
        return {
            "success": True, 
            "data": raw_result,
            "summary": summary_report
        }
    except Exception as e:
        print(f"HATA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask-doc")
def ask_document(request: QueryRequest):
    """Belge (PDF) Soruları için (RAG)"""
    try:
        print(f"📩 Belge Sorusu: {request.question}")
        answer = agent.query_knowledge_base(request.question)
        return {
            "success": True,
            "answer": answer
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

        # BURASI DEĞİŞTİ: Artık 'summarize' değil 'ingest' kullanıyoruz
        summary = agent.ingest_document(content, filename)
        
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

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)