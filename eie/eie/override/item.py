from erpnext.stock.doctype.item.item import Item as _Item
import frappe
from .purchase_receipt import get_qr_code


class Item(_Item):
    def generate_qr_code(self):
        model_no = self.model_no
        qrcode = self.item_code
        if self.barcodes:
            qrcode = f"{qrcode}, {self.barcodes[0].barcode}"
        if model_no:
            qrcode = f"{qrcode}, {model_no}"
        return f'''<img src="data:image/png;base64,{get_qr_code(qrcode)}">'''
    
    
        