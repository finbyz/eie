// frappe.provide('erpnext.accounts.dimensions');
// // Override because of price list rate changes when change warehouse in delivery note
// erpnext.TransactionController = class TransactionController extends erpnext.taxes_and_totals {
//     batch_nofunction(doc, cdt, cdn) {
//         let item = frappe.get_doc(cdt, cdn);
//         // this.apply_price_list(item, true);
//     }
// }