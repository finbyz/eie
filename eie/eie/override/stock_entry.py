from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry as _StockEntry
import frappe
from .purchase_receipt import get_qr_code


class StockEntry(_StockEntry):
    def generate_qr_code(self, idx):
        doc = self.items[idx - 1]
        model_no = frappe.db.get_value("Item", doc.item_code, "model_no")
        qrcode = doc.item_code
        if model_no:
            qrcode = f"{qrcode}, {model_no}"
        qrcode = f"{qrcode}, {self.name}"
        return f'''<img src="data:image/png;base64,{get_qr_code(qrcode)}">'''