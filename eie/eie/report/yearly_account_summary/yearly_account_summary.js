frappe.query_reports["Yearly Account Summary"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": "Company",
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1
        },
        {
            "fieldname": "fiscal_year",
            "label": "Fiscal Year",
            "fieldtype": "Link",
            "options": "Fiscal Year",
            "reqd": 1
        }
    ]
};
