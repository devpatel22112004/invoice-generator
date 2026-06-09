# 📄 Invoice Generator

A simple, open-source **GST-compliant invoice generator** for Indian businesses. Fill in your company details, buyer details, and line items — the app automatically calculates **CGST / SGST / IGST** and lets you download a polished, print-ready **PDF invoice** instantly.

> **Stack:** Python (Flask) + ReportLab + plain HTML/CSS/JS. No database, no signup — runs entirely on your machine.

---

## ✨ Features

- 🧾 **Live invoice form** — Company (seller) + Buyer blocks with GSTIN, state, contact details
- ➕ **Dynamic line items** — Add/remove rows with description, HSN/SAC code, quantity, unit, rate
- 💸 **Auto GST math** — Live subtotal, discount, taxable value, and tax split
- 🇮🇳 **CGST + SGST or IGST** — Auto-suggested based on seller vs buyer state; manually overridable
- 📊 **Standard GST rates** — 0%, 5%, 12%, 18%, 28% (configurable)
- 🏦 **Bank details & terms** — Optional blocks included in the PDF
- 📥 **One-click PDF download** — Professionally formatted with ReportLab
- 🎨 **Clean, modern UI** — Pure HTML/CSS, no framework bloat
- 🔓 **Open source** — MIT licensed, customize freely

---

## 📸 Screenshots

> *(Add screenshots of the form and a sample PDF after running the app — place them in a `screenshots/` folder and link them here.)*

```markdown
![Form](screenshots/form.png)
![Sample PDF](screenshots/sample-pdf.png)
```

---

## 🛠 Tech Stack

| Layer    | Technology |
|----------|------------|
| Backend  | Python 3.10+, Flask 3.x |
| PDF      | ReportLab 4.x |
| Frontend | Jinja2 templates, vanilla JS, plain CSS |
| Storage  | None (form-state only — v1) |

---

## 🚀 Installation

### Prerequisites
- **Python 3.10 or higher** — [download here](https://www.python.org/downloads/)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/invoice-generator.git
cd invoice-generator

# 2. Create a virtual environment
python -m venv venv

# 3. Activate the virtual environment
# Windows (PowerShell):
venv\Scripts\Activate.ps1
# Windows (CMD):
venv\Scripts\activate.bat
# macOS / Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the app
flask run
```

Open your browser and visit: **http://127.0.0.1:5000/**

You can also run it directly with:
```bash
python app.py
```

---

## 📖 Usage

1. **Fill in your company details** — Section 1 (seller).
2. **Fill in buyer details** — Section 2.
3. **Set invoice metadata** — Section 3 (number, date, GST rate, tax type).
4. **Add line items** — Section 4. Use the **+ Add Item** button for multiple rows.
5. **Apply discount** (optional) — Section 5.
6. **Review live totals** — Section 6 updates as you type.
7. **(Optional)** Add bank details and terms — Section 7.
8. **Click "⬇ Download PDF"** — Your invoice is generated and downloaded.

> 💡 **Tip:** If the seller state and buyer state match, the app auto-selects **CGST + SGST (intra-state)**. If they differ, it auto-selects **IGST (inter-state)**. You can override this manually.

---

## 🇮🇳 How GST is Calculated

The app follows standard Indian GST rules:

| Scenario                              | Tax Type            | Split                       |
|---------------------------------------|---------------------|-----------------------------|
| Seller state = Buyer state (intra-state) | **CGST + SGST**     | Half the rate each (e.g. 18% → CGST 9% + SGST 9%) |
| Seller state ≠ Buyer state (inter-state) | **IGST**            | Full rate as IGST           |

**Formula:**
```
taxable_value = subtotal − discount
cgst          = taxable_value × (gst_rate / 2) / 100
sgst          = taxable_value × (gst_rate / 2) / 100
igst          = taxable_value × gst_rate / 100
grand_total   = taxable_value + cgst + sgst + igst
```

The total is computed **server-side** in `app.py` so the PDF math is always correct, even if the browser-side live preview is bypassed.

---

## 🗂 Project Structure

```
invoice-generator/
├── app.py                  # Flask app + PDF generation logic (ReportLab)
├── requirements.txt        # Python dependencies
├── README.md               # You are here
├── LICENSE                 # MIT license
├── .gitignore              # Python standard ignores
├── static/
│   ├── css/
│   │   └── style.css       # Form styling
│   └── js/
│       └── invoice.js      # Live GST math, dynamic rows
└── templates/
    ├── base.html           # Layout shell
    └── index.html          # Invoice entry form
```

---

## 🛣 Roadmap

**v1 (current) — Frontend only**
- ✅ Invoice form with live totals
- ✅ GST split (CGST/SGST or IGST)
- ✅ PDF download via ReportLab
- ✅ Auto-suggest tax type based on states

**v2 — Persistence & multi-user**
- ⏳ Database (SQLite/PostgreSQL) for storing invoices
- ⏳ Company profile management (save once, reuse)
- ⏳ Invoice history & search
- ⏳ Multi-currency support

**v3 — Integrations**
- ⏳ Email invoice to buyer
- ⏳ Logo upload
- ⏳ WhatsApp share
- ⏳ REST API for third-party integrations

---

## 🤝 Contributing

Contributions are welcome! Please open an issue first to discuss what you'd like to change, then submit a pull request.

```bash
# Fork the repo, then:
git checkout -b feature/your-feature
git commit -m "Add your feature"
git push origin feature/your-feature
# Open a PR on GitHub
```

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/) and [ReportLab](https://www.reportlab.com/)
- Inspired by the need for a no-nonsense, offline-friendly invoice tool for small businesses
