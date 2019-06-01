frappe.views.calendar["Meeting"] = {
	field_map: {
		"start": "meeting_from",
		"end": "meeting_to",
		"id":"name",
		"color" : "color",
		"title": "organisation"
	},
	options: {
 		header: {
 			left: 'prev,next today',
 			center: 'title',
 			right: 'month week day'
 		}
 	},
	filters: [	
		{
			"fieldtype": "Select",
			"fieldname": "party_type",
			"options": "Lead\nCustomer",
			"label": __("Party Type")
		},
	],
	
 	/* color_map: {
 		"yellow": "yellow",
 		"red": "red"
 	},
	
	employee_map: {},
 	color_css: [
 		"turquoise",
 		"green-sea",
 		"emerald",
 		"nephritis",
 		"peter-river",
 		"belize-hole",
 		"amethyst",
 		"wisteria",
 		"wet-asphalt",
 		"midnight-blue",
 		"sunflower",
 		"another-orange",
 		"carrot",
 		"pumpkin",
 		"alizarin",
 		"pomegranate",
 		"clouds",
 		"silver",
 		"concrete",
 		"asbestos"
 	],
	cnt: 0,
 	get_color: function() {
 		this.cnt++;
 		if (this.cnt == this.color_css.length) this.cnt = 0;
 		return this.color_css[this.cnt];
 	}, */
	
	get_css_class: function(data) {
 		if(data.party_type == "Lead") {
			return "danger";
 		} else if(data.party_type == "Customer") {
 			return "warning";
 		}
 	},
	
	
	
	gantt: true,
	get_events_method: "eie.eie.doctype.meeting.meeting.get_events"
};