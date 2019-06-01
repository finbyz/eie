frappe.views.calendar["Meeting Schedule"] = {
	field_map: {
		"start": "scheduled_from",
		"end": "scheduled_to",
		"id": "name",
		"title": "organisation"
	},
	gantt: true,
	get_events_method: "eie.eie.doctype.meeting_schedule.meeting_schedule.get_events"
};