if(cur_frm.doc.company == "EIE Instruments Pvt. Ltd."){
    cur_frm.fields_dict["items"].grid.get_field("item_code").get_query = function(doc) {
        return {
            query: "eie.api.new_item_query",
            filters:{'dont_allow_sales_in_eie':0,'is_sales_item': 1}
        }
    }
}else{
    cur_frm.fields_dict["items"].grid.get_field("item_code").get_query = function(doc) {
        return {
            query: "eie.api.new_item_query",
            filters: {'is_sales_item': 1}
        }
    }
}

erpnext.selling.QuotationController = erpnext.selling.QuotationController.extend({
    refresh: function(doc, dt, dn) {
		this._super(doc, dt, dn);
        if(doc.company == "EIE Instruments Pvt. Ltd."){
            cur_frm.fields_dict["items"].grid.get_field("item_code").get_query = function(doc) {
                return {
                    query: "eie.api.new_item_query",
                    filters:{'dont_allow_sales_in_eie':0,'is_sales_item': 1}
                }
            }
        }else{
            cur_frm.fields_dict["items"].grid.get_field("item_code").get_query = function(doc) {
                return {
                    query: "eie.api.new_item_query",
                    filters: {'is_sales_item': 1}
                }
            }
        }
    },
    onload: function(doc, dt, dn) {
        if(doc.company == "EIE Instruments Pvt. Ltd."){
            cur_frm.fields_dict["items"].grid.get_field("item_code").get_query = function(doc) {
                return {
                    query: "eie.api.new_item_query",
                    filters:{'dont_allow_sales_in_eie':0,'is_sales_item': 1}
                }
            }
        }else{
            cur_frm.fields_dict["items"].grid.get_field("item_code").get_query = function(doc) {
                return {
                    query: "eie.api.new_item_query",
                    filters: {'is_sales_item': 1}
                }
            }
        }
    },
    naming_series: function(frm){
        if(doc.company == "EIE Instruments Pvt. Ltd."){
            cur_frm.fields_dict["items"].grid.get_field("item_code").get_query = function(doc) {
                return {
                    query: "eie.api.new_item_query",
                    filters:{'dont_allow_sales_in_eie':0,'is_sales_item': 1}
                }
            }
        }else{
            cur_frm.fields_dict["items"].grid.get_field("item_code").get_query = function(doc) {
                return {
                    query: "eie.api.new_item_query",
                    filters: {'is_sales_item': 1}
                }
            }
        }
    }
});

cur_frm.script_manager.make(erpnext.selling.QuotationController);