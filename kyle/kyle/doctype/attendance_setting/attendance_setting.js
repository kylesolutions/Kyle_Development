// Copyright (c) 2025, Vivek and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Setting", {
mark_attendance: function(frm) {
		const from_date = frm.doc.from_date;
		const to_date = frm.doc.to_date;

		if (!from_date || !to_date) {
			frappe.msgprint("Please select both From Date and To Date.");
			return;
		}

		if (new Date(to_date) < new Date(from_date)) {
			frappe.msgprint("To Date cannot be earlier than From Date.");
			return;
		}

		frappe.call({
			method: "kyle.customisations.attendance.process_attendance",
			freeze: true,
			args: {
				from_date: from_date,
				to_date: to_date
			},
			callback: function (r) {
				if (!r.exc) {
					frappe.msgprint("Attendance Processed!");
				}
			}
		});
	},
});
