import os, re, json, argparse
from datetime import datetime
import pdfplumber

# ---------- Helpers ----------
def tr_money_to_float(s: str):
    if s is None: 
        return None
    s = s.strip()
    # "4.609,24" -> 4609.24
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return None

def parse_tr_date_to_iso(s: str):
    # "16.10.2025" -> "2025-10-16"
    try:
        dt = datetime.strptime(s.strip(), "%d.%m.%Y")
        return dt.strftime("%Y-%m-%d")
    except:
        return None

def extract_text_pdfplumber(pdf_path: str):
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text(layout=True)
            if t:
                text_parts.append(t)
    return "\n".join(text_parts).strip()

def normalize_text_for_regex(text: str):
    # pdfplumber layout=True boşlukları çok şişiriyor.
    # Regex yakalamada daha stabil olması için satır sonlarını koruyup fazla space’i azaltıyoruz.
    lines = []
    for ln in text.splitlines():
        ln2 = re.sub(r"[ \t]+", " ", ln).strip()
        if ln2:
            lines.append(ln2)
    return "\n".join(lines)

# ---------- Common regex ----------
re_inv_id = re.compile(r"\b(INV-\d{4}-\d{6})\b")
re_srv_id = re.compile(r"\b(SRV-\d{4}-\d{6})\b")
re_hr_id  = re.compile(r"\b(HR-\d{4}-\d{6})\b")

re_date = re.compile(r"\bTarih:\s*(\d{2}\.\d{2}\.\d{4})\b")
re_currency = re.compile(r"\bPara Birimi:\s*([A-Z]{3})\b")
re_vendor = re.compile(r"\bTedarikçi:\s*(.+)$", re.MULTILINE)

# Totals (Invoice/Service)
re_subtotal = re.compile(r"\bAra Toplam:\s*([\d\.\,]+)\b")
re_vat_total = re.compile(r"\bKDV Toplam:\s*([\d\.\,]+)\b")
re_grand_total = re.compile(r"\bGenel Toplam:\s*([\d\.\,]+)\b")

# Service VAT: "KDV (%20): 286,66"
re_srv_vat = re.compile(r"\bKDV\s*\(%\s*(\d{1,2})\)\s*:\s*([\d\.\,]+)\b")

# ---------- Invoice parsing ----------
# satır örneği: "Elma (kg) 20 50,92 %1 1.018,40"
re_line = re.compile(
    r"^(?P<name>.+?)\s*\((?P<unit>[^)]+)\)\s+"
    r"(?P<qty>\d+)\s+"
    r"(?P<unit_price>[\d\.\,]+)\s+"
    r"%\s*(?P<vat>\d+)\s+"
    r"(?P<net>[\d\.\,]+)\s*$",
    re.MULTILINE
)

def parse_invoice(raw_text: str, source_pdf: str):
    inv_m = re_inv_id.search(raw_text)
    if not inv_m:
        return None
    doc_id = inv_m.group(1)

    date_m = re_date.search(raw_text)
    date_iso = parse_tr_date_to_iso(date_m.group(1)) if date_m else None

    cur_m = re_currency.search(raw_text)
    currency = cur_m.group(1) if cur_m else None

    ven_m = re_vendor.search(raw_text)
    vendor = ven_m.group(1).strip() if ven_m else None

    subtotal = tr_money_to_float(re_subtotal.search(raw_text).group(1)) if re_subtotal.search(raw_text) else None
    vat_total = tr_money_to_float(re_vat_total.search(raw_text).group(1)) if re_vat_total.search(raw_text) else None
    grand_total = tr_money_to_float(re_grand_total.search(raw_text).group(1)) if re_grand_total.search(raw_text) else None

    lines = []
    for m in re_line.finditer(raw_text):
        name = m.group("name").strip()
        unit = m.group("unit").strip()
        qty = int(m.group("qty"))
        unit_price = tr_money_to_float(m.group("unit_price"))
        vat_rate = int(m.group("vat")) / 100.0
        net_total = tr_money_to_float(m.group("net"))
        lines.append({
            "name": name,
            "unit": unit,
            "qty": qty,
            "unit_price": unit_price,
            "vat_rate": vat_rate,
            "net_total": net_total
        })

    return {
        "doc_type": "invoice",
        "doc_id": doc_id,
        "source_pdf": source_pdf,
        "date": date_iso,
        "currency": currency,
        "vendor": vendor,
        "lines": lines,
        "subtotal": subtotal,
        "vat_total": vat_total,
        "grand_total": grand_total,
        "raw_text": raw_text
    }

# ---------- Service parsing ----------
re_srv_header = re.compile(
    r"Rapor No:\s*(SRV-\d{4}-\d{6})\s*\|\s*Tarih:\s*(\d{2}\.\d{2}\.\d{4})\s*\|\s*Durum:\s*(.+)$",
    re.MULTILINE
)
re_priority = re.compile(r"\bÖncelik:\s*([^\|]+)\|\s*SLA:\s*(.+)$", re.MULTILINE)
re_location = re.compile(r"\bLokasyon:\s*([^\|]+)\|\s*Şube/DM:\s*([^\|]+)\|\s*Depo:\s*(.+)$", re.MULTILINE)
re_machine  = re.compile(r"\bMakine:\s*(.+?)\|\s*Seri No:\s*(.+)$", re.MULTILINE)
re_tech     = re.compile(r"\bServis Teknisyeni:\s*(.+)$", re.MULTILINE)

def extract_section(raw_text: str, start_title: str, next_titles: list):
    # Basit bölüm çıkarıcı: "Arıza Tanımı" -> sonraki başlığa kadar
    s = raw_text
    start_idx = s.find(start_title)
    if start_idx == -1:
        return None
    start_idx += len(start_title)
    end_idx = len(s)
    for nt in next_titles:
        ni = s.find(nt, start_idx)
        if ni != -1 and ni < end_idx:
            end_idx = ni
    chunk = s[start_idx:end_idx].strip()
    return chunk if chunk else None

re_cost_line = re.compile(r"^(?P<item>.+?)\s+(?P<qty>[\d\.\,]+|-\s*)\s*(?P<unit_price>[\d\.\,]+|-\s*)\s+(?P<total>[\d\.\,]+)\s*$", re.MULTILINE)

def parse_service(raw_text: str, source_pdf: str):
    srv_m = re_srv_id.search(raw_text)
    if not srv_m:
        return None
    doc_id = srv_m.group(1)

    header_m = re_srv_header.search(raw_text)
    status = None
    date_iso = None
    if header_m:
        date_iso = parse_tr_date_to_iso(header_m.group(2))
        status = header_m.group(3).strip()

    pr_m = re_priority.search(raw_text)
    priority = pr_m.group(1).strip() if pr_m else None
    sla = pr_m.group(2).strip() if pr_m else None

    loc_m = re_location.search(raw_text)
    location = loc_m.group(1).strip() if loc_m else None
    branch = loc_m.group(2).strip() if loc_m else None
    depot = loc_m.group(3).strip() if loc_m else None

    mac_m = re_machine.search(raw_text)
    machine = mac_m.group(1).strip() if mac_m else None
    serial_no = mac_m.group(2).strip() if mac_m else None

    tech_m = re_tech.search(raw_text)
    technician = tech_m.group(1).strip() if tech_m else None

    fault_desc = extract_section(raw_text, "Arıza Tanımı", ["Yapılan İşlemler", "Maliyet Özeti", "Ara Toplam"])
    actions = extract_section(raw_text, "Yapılan İşlemler", ["Maliyet Özeti", "Ara Toplam"])
    actions_list = []
    if actions:
        for ln in actions.splitlines():
            ln = ln.strip()
            if ln.startswith("-") or ln.startswith("•"):
                actions_list.append(ln.lstrip("-•").strip())
            elif ln:
                # bazı dosyalarda tire yoksa
                actions_list.append(ln)

    cost_items = []
    cost_chunk = extract_section(raw_text, "Maliyet Özeti", ["Ara Toplam", "KDV", "Genel Toplam"])
    if cost_chunk:
        for m in re_cost_line.finditer(cost_chunk):
            item = m.group("item").strip()
            qty = m.group("qty").strip()
            unit_price = m.group("unit_price").strip()
            total = m.group("total").strip()
            cost_items.append({
                "item": item,
                "qty": None if qty.startswith("-") else tr_money_to_float(qty),
                "unit_price": None if unit_price.startswith("-") else tr_money_to_float(unit_price),
                "total": tr_money_to_float(total)
            })

    subtotal = tr_money_to_float(re_subtotal.search(raw_text).group(1)) if re_subtotal.search(raw_text) else None
    vat_rate = None
    vat_amount = None
    srv_vat_m = re_srv_vat.search(raw_text)
    if srv_vat_m:
        vat_rate = int(srv_vat_m.group(1)) / 100.0
        vat_amount = tr_money_to_float(srv_vat_m.group(2))
    total = tr_money_to_float(re_grand_total.search(raw_text).group(1)) if re_grand_total.search(raw_text) else None

    return {
        "doc_type": "service_report",
        "doc_id": doc_id,
        "source_pdf": source_pdf,
        "date": date_iso,
        "status": status,
        "priority": priority,
        "sla": sla,
        "location": location,
        "branch_dm": branch,
        "depot": depot,
        "machine": machine,
        "serial_no": serial_no,
        "technician": technician,
        "fault_description": fault_desc,
        "actions": actions_list,
        "cost_items": cost_items,
        "subtotal": subtotal,
        "vat_rate": vat_rate,
        "vat_amount": vat_amount,
        "grand_total": total,
        "raw_text": raw_text
    }

# ---------- HR parsing ----------
# "Yazı No: HR-2024-000001 | Tarih: 14.07.2024 | Lokasyon: Adana"
re_hr_header = re.compile(
    r"Yazı No:\s*(HR-\d{4}-\d{6})\s*\|\s*Tarih:\s*(\d{2}\.\d{2}\.\d{4})\s*\|\s*Lokasyon:\s*(.+)$",
    re.MULTILINE
)
re_subject = re.compile(r"\bKonu:\s*(.+)$", re.MULTILINE)
re_recipient = re.compile(r"\bAlıcı:\s*(.+?)\s*\|\s*Departman:\s*(.+)$", re.MULTILINE)
re_editor = re.compile(r"\bDüzenleyen:\s*(.+)$", re.MULTILINE)

def parse_hr(raw_text: str, source_pdf: str, hr_kind: str):
    hr_m = re_hr_id.search(raw_text)
    if not hr_m:
        return None
    doc_id = hr_m.group(1)

    head_m = re_hr_header.search(raw_text)
    date_iso = parse_tr_date_to_iso(head_m.group(2)) if head_m else None
    location = head_m.group(3).strip() if head_m else None

    subj = re_subject.search(raw_text)
    subject = subj.group(1).strip() if subj else None

    rec = re_recipient.search(raw_text)
    recipient_name = rec.group(1).strip() if rec else None
    recipient_dept = rec.group(2).strip() if rec else None

    edt = re_editor.search(raw_text)
    editor = edt.group(1).strip() if edt else None

    # Body: alıcı satırından sonra not kısmına kadar
    body = raw_text
    # "Düzenleyen:" sonrası gövde başlıyor gibi
    idx = body.find("Düzenleyen:")
    if idx != -1:
        body = body[idx:]
        # düzenleyen satırını da içeriyor olabilir
    # Not'tan önce kes
    not_idx = body.find("Not:")
    if not_idx != -1:
        body = body[:not_idx].strip()

    return {
        "doc_type": "hr_letter",
        "hr_kind": hr_kind,  # "warning" / "promotion"
        "doc_id": doc_id,
        "source_pdf": source_pdf,
        "date": date_iso,
        "location": location,
        "subject": subject,
        "recipient": {
            "name": recipient_name,
            "department": recipient_dept
        },
        "issuer": editor,
        "body_text": body.strip() if body else None,
        "raw_text": raw_text
    }

# ---------- Router ----------
def detect_kind_from_filename(filename: str):
    fn = filename.upper()
    if "_FATURA_" in fn:
        return "invoice"
    if "_SERVIS_" in fn:
        return "service"
    if "_IK_UYARI_" in fn:
        return "hr_warning"
    if "_IK_TERFI_" in fn:
        return "hr_promotion"
    return "unknown"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf-dir", default="./pdfs")
    ap.add_argument("--out-dir", default="./json_docs")
    args = ap.parse_args()

    pdf_dir = args.pdf_dir
    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)

    index_path = os.path.join(out_dir, "index.jsonl")
    idx_fp = open(index_path, "w", encoding="utf-8")

    files = sorted([f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")])

    ok, fail = 0, 0
    for fn in files:
        pdf_path = os.path.join(pdf_dir, fn)
        try:
            raw = extract_text_pdfplumber(pdf_path)
            if not raw.strip():
                fail += 1
                continue
            raw_norm = normalize_text_for_regex(raw)

            kind = detect_kind_from_filename(fn)

            doc = None
            if kind == "invoice":
                doc = parse_invoice(raw_norm, fn)
            elif kind == "service":
                doc = parse_service(raw_norm, fn)
            elif kind == "hr_warning":
                doc = parse_hr(raw_norm, fn, "warning")
            elif kind == "hr_promotion":
                doc = parse_hr(raw_norm, fn, "promotion")
            else:
                # fallback: içerikten tespit denemesi
                if re_inv_id.search(raw_norm):
                    doc = parse_invoice(raw_norm, fn)
                elif re_srv_id.search(raw_norm):
                    doc = parse_service(raw_norm, fn)
                elif re_hr_id.search(raw_norm):
                    # içerikten konuya göre ayırmak zor; default letter
                    doc = parse_hr(raw_norm, fn, "unknown")

            if not doc:
                fail += 1
                continue

            out_name = f"{doc['doc_id']}.json"
            out_path = os.path.join(out_dir, out_name)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)

            # index line
            idx = {
                "doc_id": doc.get("doc_id"),
                "doc_type": doc.get("doc_type"),
                "source_pdf": doc.get("source_pdf"),
                "date": doc.get("date"),
            }
            if doc.get("doc_type") == "hr_letter":
                idx["hr_kind"] = doc.get("hr_kind")
                idx["subject"] = doc.get("subject")
            if doc.get("doc_type") == "invoice":
                idx["grand_total"] = doc.get("grand_total")
                idx["vendor"] = doc.get("vendor")
            if doc.get("doc_type") == "service_report":
                idx["status"] = doc.get("status")
                idx["machine"] = doc.get("machine")
                idx["grand_total"] = doc.get("grand_total")

            idx_fp.write(json.dumps(idx, ensure_ascii=False) + "\n")
            ok += 1

        except Exception:
            fail += 1

    idx_fp.close()
    print(f"✅ JSON yazılan: {ok}")
    print(f"❌ Başarısız/atlanmış: {fail}")
    print(f"📁 Output: {out_dir}")
    print(f"🧾 Index: {index_path}")

if __name__ == "__main__":
    main()
