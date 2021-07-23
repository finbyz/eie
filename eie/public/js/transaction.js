frappe.provide('erpnext.accounts.dimensions');
// Override because of price list rate changes when change warehouse in delivery note
erpnext.TransactionController = erpnext.TransactionController.extend({
    batch_no: function(doc, cdt, cdn) {
        let item = frappe.get_doc(cdt, cdn);
        // this.apply_price_list(item, true);
    },
});