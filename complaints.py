"""
complaints.py
=============
Data-layer for the Wasaly complaint system.

Complaint categories
--------------------
  - Wrong Items
  - Missing Items
  - Late Delivery
  - Poor Food Quality
  - Payment Issue
  - Rude Behavior
  - Other

Complaint statuses
------------------
  Open  →  In Review  →  Resolved
"""

import csv
import os
import uuid
from datetime import datetime

COMPLAINTS_CSV = "complaints_data.csv"
COMPLAINTS_HEADERS = [
    "complaint_id",
    "order_id",
    "restaurant_id",
    "restaurant_name",
    "user_email",
    "category",
    "description",
    "status",           # Open | In Review | Resolved
    "admin_notes",
    "timestamp",
    "updated_at",
]

COMPLAINT_CATEGORIES = [
    "Wrong Items",
    "Missing Items",
    "Late Delivery",
    "Poor Food Quality",
    "Payment Issue",
    "Rude Behavior",
    "Other",
]

COMPLAINT_STATUS_STYLES = {
    "Open":      ("#ef4444", "#fef2f2"),
    "In Review": ("#f59e0b", "#fffbeb"),
    "Resolved":  ("#10b981", "#ecfdf5"),
}


def _current_ts():
    return datetime.now().isoformat(timespec="seconds")


def _ensure_csv():
    if not os.path.exists(COMPLAINTS_CSV):
        with open(COMPLAINTS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COMPLAINTS_HEADERS)
            writer.writeheader()


def load_complaints():
    _ensure_csv()
    rows = []
    with open(COMPLAINTS_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            normalized = {h: row.get(h, "").strip() for h in COMPLAINTS_HEADERS}
            if normalized["complaint_id"]:
                rows.append(normalized)
    return rows


def _save_complaints(complaints):
    with open(COMPLAINTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COMPLAINTS_HEADERS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(complaints)


def submit_complaint(order_id, restaurant_id, restaurant_name,
                     user_email, category, description):
    """
    Create a new complaint linked to *order_id*.
    Returns the generated complaint_id string.
    """
    _ensure_csv()
    complaint_id = "CMP-" + uuid.uuid4().hex[:8].upper()
    ts = _current_ts()
    row = {
        "complaint_id":    complaint_id,
        "order_id":        order_id,
        "restaurant_id":   restaurant_id,
        "restaurant_name": restaurant_name,
        "user_email":      user_email,
        "category":        category,
        "description":     description,
        "status":          "Open",
        "admin_notes":     "",
        "timestamp":       ts,
        "updated_at":      ts,
    }
    with open(COMPLAINTS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COMPLAINTS_HEADERS, extrasaction="ignore")
        writer.writerow(row)
    return complaint_id


def get_complaints_for_user(email):
    return [c for c in load_complaints()
            if c["user_email"].lower() == email.strip().lower()]


def get_complaint_by_id(complaint_id):
    for c in load_complaints():
        if c["complaint_id"] == complaint_id:
            return c
    return None


def update_complaint(complaint_id, status=None, admin_notes=None):
    """Update status and/or admin_notes for a complaint. Returns True on success."""
    complaints = load_complaints()
    found = False
    for c in complaints:
        if c["complaint_id"] == complaint_id:
            if status is not None:
                c["status"] = status
            if admin_notes is not None:
                c["admin_notes"] = admin_notes
            c["updated_at"] = _current_ts()
            found = True
            break
    if found:
        _save_complaints(complaints)
    return found


def complaint_exists_for_order(order_id, user_email):
    """Return True if the user already filed a complaint for this order."""
    for c in load_complaints():
        if (c["order_id"] == order_id and
                c["user_email"].lower() == user_email.strip().lower()):
            return True
    return False