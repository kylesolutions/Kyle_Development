import frappe
from frappe.utils import get_datetime, time_diff_in_hours, getdate



@frappe.whitelist()
def process_attendance(from_date=None, to_date=None):

    if not from_date or not to_date:
        frappe.throw("Both From Date and To Date are required.")

    from_date = getdate(from_date)
    to_date = getdate(to_date)

    attendance_settings = frappe.get_single("Attendance Setting")
    present_buffer_hour = attendance_settings.make_attendance_present_buffer_hour or 8
    absent_buffer_hour = attendance_settings.make_attendance_half_day_buffer_hour or 4
    hr_email = attendance_settings.email_for_send_attendance_alert

    if not hr_email:
        frappe.throw("Email address for attendance alerts is not configured in Attendance Setting. Please set it before creating attendance.")

    try:
        check_ins = frappe.get_all(
            "Employee Checkin",
            filters={
                "attendance": ["is", "not set"],
                "time": ["between", [from_date, to_date]]
            },
            fields=["name", "employee", "time", "shift"],
            order_by="employee ASC, time ASC"
        )

        employee_day_logs = {}
        for log in check_ins:
            log["time"] = get_datetime(log["time"])
            key = (log["employee"], log["time"].date())
            employee_day_logs.setdefault(key, []).append(log)

        for (employee, log_date), logs in employee_day_logs.items():
            if log_date < from_date or log_date > to_date:
                continue

            logs.sort(key=lambda l: l["time"])

            if len(logs) == 1:
                in_time = logs[0]["time"]
               
                subject = f"[Attendance Alert] Missing Last Punch for {employee} on {log_date}"
                message = f"""
                    <p>Dear HR,</p>
                    <p>The system detected only one check-in (Missing Last Punch) for the employee:</p>
                    <ul>
                        <li><strong>Employee:</strong> {employee}</li>
                        <li><strong>Date:</strong> {log_date}</li>
                        <li><strong>First Punch:</strong> {in_time.strftime('%H:%M:%S')}</li>
                    </ul>
                    <p>Please create a manual punch and proceed with the attendance creation process.</p>
                """
                frappe.sendmail(
                    recipients=[hr_email],
                    subject=subject,
                    message=message
                )
                continue

            first_log = logs[0]
            last_log = logs[-1]
            in_time = first_log["time"]
            out_time = last_log["time"]

            duration = time_diff_in_hours(out_time, in_time)
            if duration >= present_buffer_hour:
                status = "Present"
            elif duration >= absent_buffer_hour:
                status = "Half Day"
            else:
                status = "Absent"

            if not frappe.db.exists("Attendance", {"employee": employee, "attendance_date": log_date, "docstatus": 1}):
                attendance = frappe.get_doc({
                    "doctype": "Attendance",
                    "employee": employee,
                    "attendance_date": log_date,
                    "status": status,
                    "working_hours": duration,
                    "in_time": in_time,
                    "out_time": out_time,
                })
                attendance.insert(ignore_permissions=True)
                attendance.submit()

                for log in logs:
                    frappe.db.set_value("Employee Checkin", log["name"], "attendance", attendance.name)

        frappe.db.commit()

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Error in process_attendance")