/* Invoice Generator — live totals & GST split
 *
 * - Add / remove line item rows
 * - Compute line totals, subtotal, discount, taxable value
 * - Split GST into CGST + SGST (intra-state) or IGST (inter-state)
 * - Auto-suggest tax type when seller/buyer states change
 * - Update the summary panel in real time
 */
(function () {
    "use strict";

    const $ = (sel, root = document) => root.querySelector(sel);
    const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

    // ---------- Helpers ----------
    const money = (n) => "Rs. " + (Number(n) || 0).toLocaleString("en-IN", {
        minimumFractionDigits: 2, maximumFractionDigits: 2,
    });

    const parseNum = (v) => {
        const n = parseFloat(v);
        return isNaN(n) ? 0 : n;
    };

    // ---------- Tax type auto-suggestion ----------
    function autoSuggestTaxType() {
        const seller = ($("#company_state")?.value || "").trim().toLowerCase();
        const buyer  = ($("#buyer_state")?.value   || "").trim().toLowerCase();
        const taxSel = $("#tax_type");
        if (!seller || !buyer) return;
        if (seller === buyer) {
            taxSel.value = "CGST_SGST";
        } else {
            taxSel.value = "IGST";
        }
        // tax type change triggers recompute via the change handler below
        taxSel.dispatchEvent(new Event("change"));
    }

    // ---------- Line items ----------
    function rowAmount(row) {
        const qty  = parseNum($(".qty",  row).value);
        const rate = parseNum($(".rate", row).value);
        return Math.round(qty * rate * 100) / 100;
    }

    function addRow() {
        const tbody = $("#items-body");
        const row = document.createElement("tr");
        row.className = "item-row";
        row.innerHTML = `
            <td><input type="text" name="item_description[]" required placeholder="Item / service description"></td>
            <td><input type="text" name="item_hsn[]" placeholder="8471"></td>
            <td><input type="number" name="item_qty[]" step="0.01" min="0" value="1" class="qty"></td>
            <td><input type="text" name="item_unit[]" value="NOS"></td>
            <td><input type="number" name="item_rate[]" step="0.01" min="0" value="0" class="rate"></td>
            <td class="amount-cell">Rs. 0.00</td>
            <td><button type="button" class="btn-icon remove-row" title="Remove">✕</button></td>
        `;
        tbody.appendChild(row);
        attachRowEvents(row);
        recompute();
    }

    function removeRow(row) {
        const tbody = $("#items-body");
        if (tbody.querySelectorAll(".item-row").length <= 1) {
            // never leave the table empty
            $$("input", row).forEach(i => {
                if (i.type === "text" || i.tagName === "TEXTAREA") i.value = "";
                else if (i.type === "number") i.value = i.classList.contains("qty") ? "1" : "0";
            });
            recompute();
            return;
        }
        row.remove();
        recompute();
    }

    function attachRowEvents(row) {
        $(".qty",  row).addEventListener("input", recompute);
        $(".rate", row).addEventListener("input", recompute);
        $(".remove-row", row).addEventListener("click", () => removeRow(row));
    }

    // ---------- Totals ----------
    function recompute() {
        const rows = $$(".item-row");
        let subtotal = 0;

        rows.forEach(row => {
            const amount = rowAmount(row);
            $(".amount-cell", row).textContent = money(amount);
            subtotal += amount;
        });

        const discountPct = parseNum($("#discount_pct")?.value);
        const discount    = Math.round(subtotal * discountPct / 100 * 100) / 100;
        const taxable     = Math.round((subtotal - discount) * 100) / 100;

        const gstRate = parseNum($("#gst_rate")?.value);
        const taxType = $("#tax_type")?.value || "CGST_SGST";

        let cgst = 0, sgst = 0, igst = 0;
        if (taxType === "IGST") {
            igst = Math.round(taxable * gstRate / 100 * 100) / 100;
        } else {
            const half = gstRate / 2;
            cgst = Math.round(taxable * half / 100 * 100) / 100;
            sgst = Math.round(taxable * half / 100 * 100) / 100;
        }
        const totalTax = Math.round((cgst + sgst + igst) * 100) / 100;
        const grand    = Math.round((taxable + totalTax) * 100) / 100;

        // Update summary panel
        $("#t_subtotal").textContent   = money(subtotal);
        $("#t_discount").textContent   = "- " + money(discount);
        $("#t_taxable").textContent    = money(taxable);
        $("#t_total_tax").textContent  = money(totalTax);
        $("#t_grand").textContent      = money(grand);

        $("#t_cgst").textContent = money(cgst);
        $("#t_sgst").textContent = money(sgst);
        $("#t_igst").textContent = money(igst);

        const half = gstRate / 2;
        $("#t_cgst_pct").textContent = half.toFixed(2).replace(/\.00$/, "");
        $("#t_sgst_pct").textContent = half.toFixed(2).replace(/\.00$/, "");
        $("#t_igst_pct").textContent = gstRate.toString().replace(/\.00$/, "");

        // Toggle CGST/SGST vs IGST rows
        const showCgstSgst = (taxType !== "IGST");
        $(".cgst-row").style.display = showCgstSgst ? "" : "none";
        $(".sgst-row").style.display = showCgstSgst ? "" : "none";
        $(".igst-row").style.display = showCgstSgst ? "none" : "";
    }

    // ---------- Wire up ----------
    document.addEventListener("DOMContentLoaded", () => {
        // Existing row(s)
        $$(".item-row").forEach(attachRowEvents);

        $("#add-row").addEventListener("click", addRow);
        $("#discount_pct").addEventListener("input", recompute);
        $("#gst_rate").addEventListener("change", recompute);
        $("#tax_type").addEventListener("change", recompute);
        $("#company_state").addEventListener("change", autoSuggestTaxType);
        $("#buyer_state").addEventListener("change", autoSuggestTaxType);

        recompute();
    });
})();
