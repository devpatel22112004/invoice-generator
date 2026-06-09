"""
Invoice Generator — Flask app
Generates GST-compliant invoices (CGST/SGST/IGST) and downloads them as PDF.
"""
from io import BytesIO
from datetime import datetime

from flask import Flask, render_template, request, send_file, jsonify
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)

app = Flask(__name__)


# ---------- PDF Generation ----------

def _money(value):
    """Format a number as Indian-style money: 1,23,456.78 with two decimals."""
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        v = 0.0
    return f"Rs. {v:,.2f}"


def _parse_items(form):
    """Extract line items from the form (posted as parallel arrays)."""
    descriptions = form.getlist("item_description[]")
    hsn_codes    = form.getlist("item_hsn[]")
    quantities   = form.getlist("item_qty[]")
    units        = form.getlist("item_unit[]")
    rates        = form.getlist("item_rate[]")

    items = []
    for i, desc in enumerate(descriptions):
        desc = (desc or "").strip()
        if not desc:
            continue
        try:
            qty = float(quantities[i]) if i < len(quantities) and quantities[i] else 0
        except ValueError:
            qty = 0
        try:
            rate = float(rates[i]) if i < len(rates) and rates[i] else 0
        except ValueError:
            rate = 0
        items.append({
            "description": desc,
            "hsn":        (hsn_codes[i] if i < len(hsn_codes) else "").strip(),
            "qty":        qty,
            "unit":       (units[i] if i < len(units) else "NOS").strip() or "NOS",
            "rate":       rate,
            "amount":     round(qty * rate, 2),
        })
    return items


def _parse_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _compute_totals(data):
    """Re-compute totals server-side so the PDF is correct regardless of the form's client math."""
    items = data["items"]
    subtotal = round(sum(i["amount"] for i in items), 2)

    discount_pct = _parse_float(data.get("discount_pct"), 0)
    discount = round(subtotal * discount_pct / 100.0, 2)
    taxable = round(subtotal - discount, 2)

    gst_rate = _parse_float(data.get("gst_rate"), 0)
    tax_type = data.get("tax_type", "CGST_SGST")

    if tax_type == "IGST":
        igst = round(taxable * gst_rate / 100.0, 2)
        cgst = sgst = 0.0
    else:
        half = gst_rate / 2.0
        cgst = round(taxable * half / 100.0, 2)
        sgst = round(taxable * half / 100.0, 2)
        igst = 0.0

    total_tax = round(cgst + sgst + igst, 2)
    grand_total = round(taxable + total_tax, 2)

    return {
        "subtotal":   subtotal,
        "discount":   discount,
        "taxable":    taxable,
        "gst_rate":   gst_rate,
        "tax_type":   tax_type,
        "cgst":       cgst,
        "sgst":       sgst,
        "igst":       igst,
        "total_tax":  total_tax,
        "grand_total": grand_total,
    }


def _build_pdf(data, totals):
    """Build the invoice PDF with ReportLab and return it as bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm,  bottomMargin=15 * mm,
        title=f"Tax Invoice {data.get('invoice_number', '')}".strip(),
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=20, spaceAfter=4, textColor=colors.HexColor("#1a3d6d"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11, spaceAfter=2, textColor=colors.HexColor("#1a3d6d"))
    normal = ParagraphStyle("normal", parent=styles["Normal"], fontSize=9, leading=12)
    small  = ParagraphStyle("small",  parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.grey)
    bold   = ParagraphStyle("bold",   parent=styles["Normal"], fontSize=9, leading=12, fontName="Helvetica-Bold")

    story = []

    # ---- Title row: company name (left) + TAX INVOICE (right)
    company_name = data.get("company_name", "Your Company Name") or "Your Company Name"
    title_table = Table(
        [[Paragraph(f"<b>{company_name}</b>", h1),
          Paragraph("<para align='right'><b>TAX INVOICE</b></para>", h1)]],
        colWidths=[110 * mm, 70 * mm],
    )
    title_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(title_table)
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#1a3d6d")))
    story.append(Spacer(1, 4 * mm))

    # ---- Invoice meta + Company meta (2 columns)
    meta_left = [
        Paragraph("<b>Bill From</b>", h2),
        Paragraph(f"<b>{data.get('company_name', '')}</b>", normal),
        Paragraph(data.get("company_address", ""), normal),
        Paragraph(f"GSTIN: {data.get('company_gstin', '')}", normal),
        Paragraph(f"State: {data.get('company_state', '')}", normal),
        Paragraph(f"Phone: {data.get('company_phone', '')}", normal),
        Paragraph(f"Email: {data.get('company_email', '')}", normal),
    ]
    meta_right = [
        Paragraph("<b>Invoice Details</b>", h2),
        Paragraph(f"<b>Invoice No:</b> {data.get('invoice_number', '')}", normal),
        Paragraph(f"<b>Date:</b> {data.get('invoice_date', '')}", normal),
        Paragraph(f"<b>Due Date:</b> {data.get('due_date', '-')}", normal),
        Paragraph(f"<b>Place of Supply:</b> {data.get('place_of_supply', '')}", normal),
        Paragraph(f"<b>Tax Type:</b> {'IGST (Inter-state)' if totals['tax_type'] == 'IGST' else 'CGST + SGST (Intra-state)'}", normal),
    ]
    bill_to = [
        Paragraph("<b>Bill To</b>", h2),
        Paragraph(f"<b>{data.get('buyer_name', '')}</b>", normal),
        Paragraph(data.get("buyer_address", ""), normal),
        Paragraph(f"GSTIN: {data.get('buyer_gstin', '')}", normal),
        Paragraph(f"State: {data.get('buyer_state', '')}", normal),
        Paragraph(f"Phone: {data.get('buyer_phone', '')}", normal),
        Paragraph(f"Email: {data.get('buyer_email', '')}", normal),
    ]

    meta_table = Table(
        [[meta_left, meta_right], [bill_to, ""]],
        colWidths=[95 * mm, 85 * mm],
    )
    meta_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX",    (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f4f7fb")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 5 * mm))

    # ---- Items table
    items_header = ["#", "Description", "HSN/SAC", "Qty", "Unit", "Rate", "Amount"]
    items_rows = [items_header]
    for idx, it in enumerate(data["items"], 1):
        items_rows.append([
            str(idx),
            it["description"],
            it["hsn"],
            f"{it['qty']:.2f}",
            it["unit"],
            _money(it["rate"]),
            _money(it["amount"]),
        ])

    items_table = Table(
        items_rows,
        colWidths=[8 * mm, 60 * mm, 22 * mm, 14 * mm, 14 * mm, 28 * mm, 34 * mm],
        repeatRows=1,
    )
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3d6d")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("ALIGN",      (0, 0), (0, -1),  "CENTER"),
        ("ALIGN",      (3, 0), (-1, -1), "RIGHT"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",       (0, 0), (-1, -1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafc")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 4 * mm))

    # ---- Totals table (right-aligned)
    totals_rows = [
        ["Subtotal", _money(totals["subtotal"])],
    ]
    if totals["discount"] > 0:
        totals_rows.append([f"Discount ({data.get('discount_pct', '0')}%)", f"- {_money(totals['discount'])}"])
    totals_rows.append(["Taxable Value", _money(totals["taxable"])])

    if totals["tax_type"] == "IGST":
        totals_rows.append([f"IGST @ {totals['gst_rate']:.2f}%", _money(totals["igst"])])
    else:
        half = totals["gst_rate"] / 2
        totals_rows.append([f"CGST @ {half:.2f}%", _money(totals["cgst"])])
        totals_rows.append([f"SGST @ {half:.2f}%", _money(totals["sgst"])])

    totals_rows.append(["Total Tax", _money(totals["total_tax"])])
    totals_rows.append(["GRAND TOTAL", _money(totals["grand_total"])])

    totals_table = Table(totals_rows, colWidths=[50 * mm, 50 * mm], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("ALIGN",      (1, 0), (1, -1),  "RIGHT"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",       (0, 0), (-1, -1), 0.25, colors.grey),
        ("LINEABOVE",  (0, -1), (-1, -1), 1, colors.HexColor("#1a3d6d")),
        ("FONTNAME",   (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f4f7fb")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 6 * mm))

    # ---- Bank / Terms
    if data.get("bank_details"):
        story.append(Paragraph("<b>Bank Details</b>", h2))
        story.append(Paragraph(data["bank_details"].replace("\n", "<br/>"), normal))
        story.append(Spacer(1, 3 * mm))
    if data.get("terms"):
        story.append(Paragraph("<b>Terms &amp; Conditions</b>", h2))
        story.append(Paragraph(data["terms"].replace("\n", "<br/>"), small))

    # ---- Footer
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Paragraph(
        f"This is a computer-generated invoice. Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}.",
        small,
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ---------- Routes ----------

@app.route("/", methods=["GET"])
def index():
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("index.html", today=today)


@app.route("/generate-pdf", methods=["POST"])
def generate_pdf():
    data = {
        "company_name":     request.form.get("company_name", "").strip(),
        "company_address":  request.form.get("company_address", "").strip(),
        "company_gstin":    request.form.get("company_gstin", "").strip(),
        "company_state":    request.form.get("company_state", "").strip(),
        "company_phone":    request.form.get("company_phone", "").strip(),
        "company_email":    request.form.get("company_email", "").strip(),
        "buyer_name":       request.form.get("buyer_name", "").strip(),
        "buyer_address":    request.form.get("buyer_address", "").strip(),
        "buyer_gstin":      request.form.get("buyer_gstin", "").strip(),
        "buyer_state":      request.form.get("buyer_state", "").strip(),
        "buyer_phone":      request.form.get("buyer_phone", "").strip(),
        "buyer_email":      request.form.get("buyer_email", "").strip(),
        "invoice_number":   request.form.get("invoice_number", "").strip(),
        "invoice_date":     request.form.get("invoice_date", "").strip(),
        "due_date":         request.form.get("due_date", "").strip(),
        "place_of_supply":  request.form.get("place_of_supply", "").strip(),
        "tax_type":         request.form.get("tax_type", "CGST_SGST"),
        "gst_rate":         request.form.get("gst_rate", "0"),
        "discount_pct":     request.form.get("discount_pct", "0"),
        "bank_details":     request.form.get("bank_details", "").strip(),
        "terms":            request.form.get("terms", "").strip(),
        "items":            _parse_items(request.form),
    }

    if not data["items"]:
        return jsonify({"error": "Please add at least one line item."}), 400
    if not data["company_name"] or not data["buyer_name"]:
        return jsonify({"error": "Company name and Buyer name are required."}), 400

    totals = _compute_totals(data)
    pdf_buffer = _build_pdf(data, totals)

    inv_no = data["invoice_number"] or "INV"
    safe_inv = "".join(c for c in inv_no if c.isalnum() or c in ("-", "_")) or "INV"
    filename = f"{safe_inv}.pdf"

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
