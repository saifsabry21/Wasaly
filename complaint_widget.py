"""
complaint_widget.py
===================
Customer-facing widget: Report an Issue with an Order.

Acceptance Criteria covered
---------------------------
✓ Complaint is linked to the selected order
✓ User selects a category from the available list
✓ On successful submission the user receives a confirmation with the complaint ID
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QScrollArea, QComboBox, QTextEdit, QMessageBox,
    QSizePolicy,
)

from complaints import (
    COMPLAINT_CATEGORIES,
    COMPLAINT_STATUS_STYLES,
    get_complaints_for_user,
    submit_complaint,
    complaint_exists_for_order,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: small status badge
# ─────────────────────────────────────────────────────────────────────────────
def _badge(text):
    fg, bg = COMPLAINT_STATUS_STYLES.get(text, ("#6b7280", "#f9fafb"))
    lbl = QLabel(f"  {text}  ")
    lbl.setFixedHeight(24)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(
        f"color:{fg}; background:{bg}; border:1px solid {fg}55;"
        " border-radius:6px; font-size:11px; font-weight:700;"
    )
    return lbl


# ─────────────────────────────────────────────────────────────────────────────
# Past complaint card (read-only)
# ─────────────────────────────────────────────────────────────────────────────
class ComplaintCard(QFrame):
    def __init__(self, complaint, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; }"
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # Header row
        top = QHBoxLayout()
        cid = QLabel(f"🎫 {complaint['complaint_id']}")
        cid.setFont(QFont("Arial", 12, QFont.Bold))
        cid.setStyleSheet("color:#111827; background:transparent;")
        top.addWidget(cid)
        top.addStretch()
        top.addWidget(_badge(complaint["status"]))
        layout.addLayout(top)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#f3f4f6;")
        layout.addWidget(sep)

        def _info(text):
            lbl = QLabel(text)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color:#374151; font-size:12px; background:transparent;")
            return lbl

        layout.addWidget(_info(f"📦  Order: {complaint['order_id']}  ·  {complaint['restaurant_name']}"))
        layout.addWidget(_info(f"🏷  Category: {complaint['category']}"))
        layout.addWidget(_info(f"📝  {complaint['description']}"))

        if complaint.get("admin_notes"):
            notes_box = QFrame()
            notes_box.setStyleSheet(
                "QFrame { background:#fffbeb; border:1px solid #fde68a; border-radius:8px; }"
            )
            nb_lay = QVBoxLayout(notes_box)
            nb_lay.setContentsMargins(12, 8, 12, 8)
            nb_lay.setSpacing(4)
            nb_lay.addWidget(QLabel("Admin response:") )
            nb_lay.children()[1].setStyleSheet(
                "color:#92400e; font-size:11px; font-weight:700; background:transparent;"
            )
            note_lbl = QLabel(complaint["admin_notes"])
            note_lbl.setWordWrap(True)
            note_lbl.setStyleSheet("color:#92400e; font-size:12px; background:transparent;")
            nb_lay.addWidget(note_lbl)
            layout.addWidget(notes_box)

        ts_lbl = QLabel(f"Submitted: {complaint['timestamp']}   ·   Updated: {complaint['updated_at']}")
        ts_lbl.setStyleSheet("color:#9ca3af; font-size:11px; background:transparent;")
        layout.addWidget(ts_lbl)


# ─────────────────────────────────────────────────────────────────────────────
# Main widget
# ─────────────────────────────────────────────────────────────────────────────
class ReportIssueWidget(QWidget):
    """
    Customer widget for:
      1. Submitting a new complaint linked to an order
      2. Viewing their past complaints
    """
    go_back = pyqtSignal()

    def __init__(self, user_data, orders, parent=None):
        """
        Parameters
        ----------
        user_data : dict   – logged-in user record
        orders    : list   – all orders belonging to this user
        """
        super().__init__(parent)
        self.user_data = user_data
        self.orders    = orders          # pre-filtered to this user
        self._build_ui()
        self._populate_orders()
        self.refresh_past_complaints()

    # ── Build UI ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet("background:#f9fafb;")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet("background:#ffffff; border-bottom:1px solid #e5e7eb;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)

        back_btn = QPushButton("← Dashboard")
        back_btn.setFixedHeight(36)
        back_btn.setStyleSheet("""
            QPushButton { background:#f3f4f6; color:#374151; border:none;
                border-radius:8px; padding:0 14px; font-size:13px; font-weight:600; }
            QPushButton:hover { background:#e5e7eb; }
        """)
        back_btn.clicked.connect(self.go_back.emit)

        title = QLabel("Report an Order Issue")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color:#111827;")

        user_lbl = QLabel(f"👤 {self.user_data.get('full_name', 'Customer')}")
        user_lbl.setStyleSheet("color:#6b7280; font-size:13px;")

        hl.addWidget(back_btn)
        hl.addSpacing(12)
        hl.addWidget(title)
        hl.addStretch()
        hl.addWidget(user_lbl)
        root.addWidget(header)

        # Scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:#f9fafb; }")

        body = QWidget()
        body.setStyleSheet("background:#f9fafb;")
        self._body_layout = QVBoxLayout(body)
        self._body_layout.setContentsMargins(32, 24, 32, 32)
        self._body_layout.setSpacing(20)

        # ── New complaint form ─────────────────────────────────────────────
        form_card = QFrame()
        form_card.setStyleSheet(
            "QFrame { background:#ffffff; border:1px solid #e5e7eb; border-radius:16px; }"
        )
        form_lay = QVBoxLayout(form_card)
        form_lay.setContentsMargins(24, 20, 24, 24)
        form_lay.setSpacing(14)

        form_title = QLabel("Submit a New Complaint")
        form_title.setFont(QFont("Arial", 14, QFont.Bold))
        form_title.setStyleSheet("color:#111827; background:transparent;")
        form_lay.addWidget(form_title)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#f3f4f6;")
        form_lay.addWidget(sep)

        # Select order
        form_lay.addWidget(self._field_label("Select Order"))
        self.order_combo = QComboBox()
        self.order_combo.setFixedHeight(42)
        self.order_combo.setStyleSheet(self._combo_style())
        form_lay.addWidget(self.order_combo)

        # Category
        form_lay.addWidget(self._field_label("Issue Category"))
        self.category_combo = QComboBox()
        self.category_combo.setFixedHeight(42)
        self.category_combo.addItems(COMPLAINT_CATEGORIES)
        self.category_combo.setStyleSheet(self._combo_style())
        form_lay.addWidget(self.category_combo)

        # Description
        form_lay.addWidget(self._field_label("Describe the Issue"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Please describe what went wrong in as much detail as possible…")
        self.desc_edit.setFixedHeight(110)
        self.desc_edit.setStyleSheet("""
            QTextEdit {
                border:1px solid #d1d5db; border-radius:10px;
                padding:10px 12px; font-size:13px; background:white; color:#111827;
            }
            QTextEdit:focus { border:2px solid #f0b100; }
        """)
        form_lay.addWidget(self.desc_edit)

        # Submit button
        submit_btn = QPushButton("🚨  Submit Complaint")
        submit_btn.setFixedHeight(46)
        submit_btn.setStyleSheet("""
            QPushButton { background:#ef4444; color:white; border:none;
                border-radius:10px; font-size:14px; font-weight:700; }
            QPushButton:hover { background:#dc2626; }
        """)
        submit_btn.clicked.connect(self._submit)
        form_lay.addWidget(submit_btn)

        self._body_layout.addWidget(form_card)

        # ── Past complaints header ─────────────────────────────────────────
        past_title = QLabel("My Past Complaints")
        past_title.setFont(QFont("Arial", 14, QFont.Bold))
        past_title.setStyleSheet("color:#111827;")
        self._body_layout.addWidget(past_title)

        # Past complaints container
        self._past_container = QVBoxLayout()
        self._past_container.setSpacing(10)
        self._body_layout.addLayout(self._past_container)
        self._body_layout.addStretch()

        scroll.setWidget(body)
        root.addWidget(scroll, stretch=1)

    # ── Populate helpers ─────────────────────────────────────────────────────

    def _populate_orders(self):
        self.order_combo.clear()
        if not self.orders:
            self.order_combo.addItem("No orders found")
            return
        for o in self.orders:
            label = (
                f"#{o['order_id']}  ·  {o.get('restaurant_name','?')}  "
                f"·  EGP {o.get('total','?')}  ·  {o.get('status','?')}"
            )
            self.order_combo.addItem(label, userData=o)

    def refresh_past_complaints(self):
        # Clear old cards
        while self._past_container.count():
            item = self._past_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        email = self.user_data.get("email", "").strip().lower()
        complaints = get_complaints_for_user(email)
        complaints.sort(key=lambda c: c.get("timestamp", ""), reverse=True)

        if not complaints:
            empty = QLabel("You have not submitted any complaints yet.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                "color:#9ca3af; font-size:14px; padding:30px; background:transparent;"
            )
            self._past_container.addWidget(empty)
            return

        for c in complaints:
            self._past_container.addWidget(ComplaintCard(c))

    # ── Submit handler ───────────────────────────────────────────────────────

    def _submit(self):
        idx = self.order_combo.currentIndex()
        order = self.order_combo.itemData(idx)

        if order is None:
            QMessageBox.warning(self, "No Order", "Please select an order first.")
            return

        category    = self.category_combo.currentText()
        description = self.desc_edit.toPlainText().strip()

        if not description:
            QMessageBox.warning(self, "Missing Description",
                                "Please describe the issue before submitting.")
            return

        if len(description) < 10:
            QMessageBox.warning(self, "Too Short",
                                "Please provide a more detailed description (at least 10 characters).")
            return

        email = self.user_data.get("email", "")

        # Prevent duplicate complaints for the same order
        if complaint_exists_for_order(order["order_id"], email):
            QMessageBox.information(
                self, "Already Reported",
                f"You have already submitted a complaint for order #{order['order_id']}.\n"
                "Our team is reviewing it."
            )
            return

        complaint_id = submit_complaint(
            order_id        = order["order_id"],
            restaurant_id   = order.get("restaurant_id", ""),
            restaurant_name = order.get("restaurant_name", ""),
            user_email      = email,
            category        = category,
            description     = description,
        )

        QMessageBox.information(
            self,
            "✅  Complaint Submitted",
            f"Your complaint has been received.\n\n"
            f"Complaint ID: {complaint_id}\n"
            f"Category:     {category}\n\n"
            f"Our team will review it and get back to you shortly."
        )

        self.desc_edit.clear()
        self.refresh_past_complaints()

    # ── Style helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _field_label(text):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "color:#374151; font-size:13px; font-weight:600; background:transparent;"
        )
        return lbl

    @staticmethod
    def _combo_style():
        return """
            QComboBox {
                border:1px solid #d1d5db; border-radius:10px;
                padding:0 12px; font-size:13px; background:white; color:#111827;
            }
            QComboBox:focus { border:2px solid #f0b100; }
            QComboBox QAbstractItemView {
                background:white; color:#111827; border:1px solid #d1d5db;
                selection-background-color:#f0b100; selection-color:white;
            }
        """