# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Summary

GST-compliant invoice generator for Indian businesses — Flask + ReportLab backend, vanilla JS frontend. The user fills in seller/buyer/line items, the app computes CGST + SGST (intra-state) or IGST (inter-state) split, and downloads a polished PDF. Public repo at `https://github.com/devpatel22112004/invoice-generator`.

## Commands

```bash
# Setup (Windows PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run dev server (auto-reload)
flask run
# OR
python app.py
# → http://127.0.0.1:5000

# Syntax check (no formal test suite exists yet)
python -m py_compile app.py

# Smoke-test the PDF endpoint without a browser
python -c "from app import app; c=app.test_client(); r=c.post('/generate-pdf', data={'company_name':'X','buyer_name':'Y','item_description[]':['a'],'item_qty[]':['1'],'item_rate[]':['100'],'tax_type':'IGST','gst_rate':'18'}); print(r.status_code, r.headers.get('Content-Type'))"
```

There is **no test framework, no linter config, and no CI**. The repo is intentionally minimal.

## Architecture (the non-obvious parts)

**Single-file backend (`app.py`)** with three concerns clearly separated by section comments:

1. **PDF generation helpers** (`_money`, `_parse_items`, `_parse_float`, `_compute_totals`, `_build_pdf`) — all `_`-prefixed, all pure functions, all return BytesIO / dicts. Reusable for any future code path that needs to build a PDF.
2. **Routes** (`/`, `/generate-pdf`) — thin layer: parse form, validate, call helpers, return `send_file` or `jsonify(error)`.
3. **`__main__` block** — debug server on `127.0.0.1:5000`.

**Form contract** — `index.html` posts `item_description[]`, `item_hsn[]`, `item_qty[]`, `item_unit[]`, `item_rate[]` as **parallel arrays** (not nested objects). `_parse_items` reconstructs rows by index. Any new item field must be added to **both** the template and `_parse_items` in the same order.

**Tax type values** — exactly `"CGST_SGST"` or `"IGST"` (string, with underscore). Used in the form's `<select>`, the JS, the `_compute_totals` branching, and the PDF label. Don't normalize or rename without grepping all four locations.

## GST Calculation Rules (Indian Tax Law)

The math is **always recomputed server-side in `_compute_totals`**, never trusted from the client. The browser-side `recompute()` in `invoice.js` is a UX preview only.

- `taxable = subtotal - discount` (discount is a percentage, applied to subtotal before tax)
- **Intra-state** (`tax_type == "CGST_SGST"`, seller state == buyer state): `cgst = sgst = taxable × (gst_rate / 2) / 100`
- **Inter-state** (`tax_type == "IGST"`): `igst = taxable × gst_rate / 100`
- `grand_total = taxable + cgst + sgst + igst`
- All money values rounded to 2 decimal places using `round(..., 2)`.

**Auto-suggestion rule** (in `invoice.js` `autoSuggestTaxType`): seller state == buyer state → CGST_SGST, otherwise IGST. Fires on `change` of either state input. The user can manually override.

## PDF Layout (ReportLab)

`_build_pdf` builds a `story` of flowables in this fixed order:
1. Title row (company name + "TAX INVOICE" header) with `HRFlowable` underline
2. 2×2 meta grid (Bill From / Invoice Details / Bill To / empty)
3. Line items table (header repeats on multi-page via `repeatRows=1`)
4. Right-aligned totals table (with conditional CGST+SGST or IGST rows)
5. Optional bank details & terms
6. Footer with generation timestamp

**Color tokens** — the navy `#1a3d6d` is used in three places: the HTML header/title bar (CSS), ReportLab `h1`/`h2` styles, and table header backgrounds. To rebrand, change all three.

**Filename sanitization** — `inv_no` is stripped to alphanumerics + `-_` before being used as the download filename (see lines 322–324 of `app.py`).

## Frontend Conventions

- **No frameworks, no build step.** Vanilla JS in `static/js/invoice.js` is wrapped in an IIFE with `"use strict"`. `document.addEventListener("DOMContentLoaded", ...)` wires everything up.
- **No data persistence.** All form state is in DOM. Reload = empty form.
- **Datalist for Indian states** (`#states-list` in `index.html`) — autocomplete, not a `<select>`. Users can type non-listed values.
- **Item rows never empty** — `removeRow` clears the last row's inputs instead of removing it, so the form is always submittable.

## Where Things Live (for grep)

- All money/percentage formatting: `_money()` (Python) and `money()` (JS) — **two implementations that must agree**.
- All validation: only in the `generate_pdf` route (server-side). The form uses `required` attributes only.
- All styling: `static/css/style.css` (CSS custom properties at `:root` — change colors there).
- The brand string "Acme Traders" appears as default values in `index.html` — these are just placeholders the form pre-fills, not part of the app's identity.

## Roadmap (from README, also relevant here)

**v2** — Database (SQLite likely), company profile save, invoice history. The `_build_pdf` / `_compute_totals` split is designed to make this easy: persist the `data` dict, persist computed `totals` if desired.

**v3** — Logo upload, email send, WhatsApp share, REST API. Logo upload will require `werkzeug.utils.secure_filename` and a new field in the form/items table.

When implementing v2+, preserve the parallel-array form contract OR migrate the form to send a single JSON payload and update `_parse_items` accordingly — don't half-migrate.
