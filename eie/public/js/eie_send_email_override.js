function validate_email(email) {
    const email_regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return email_regex.test(email);
}

frappe.ui.form.send_email = function(frm) {
    console.log("isnfh");
    const other_emails_raw = frm.doc.other_emails || "";
    const other_emails = other_emails_raw
        .split(",")
        .map(e => e.trim())
        .filter(e => e && validate_email(e));

    new frappe.views.CommunicationComposer({
        doc: frm.doc,
        subject: __("Regarding {0}", [frm.doc.name]),
        recipients: frm.doc.contact_email || "",
        cc: other_emails.join(", "),
    });
};