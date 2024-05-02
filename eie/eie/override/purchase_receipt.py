from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt as _PurchaseReceipt
import frappe
from pyqrcode import create as qrcreate
import io
import base64

def get_qr_code(qrcode):
    qr_image = io.BytesIO()
    url = qrcreate(qrcode, error="L")
    url.png(qr_image, scale=4, quiet_zone=1)
    return base64.b64encode(qr_image.getvalue()).decode("ascii")

class PurchaseReceipt(_PurchaseReceipt):
    def generate_qr_code(self, idx):
        doc = self.items[idx - 1]
        model_no = frappe.db.get_value("Item", doc.item_code, "model_no")
        qrcode = doc.item_code
        if model_no:
            qrcode = f"{qrcode}, {model_no}"
        qrcode = f"{qrcode}, {self.name}"
        return f'''<img src="data:image/png;base64,{get_qr_code(qrcode)}">'''
