"""
admin_complaints.py
===================
Admin-facing widget: Handle Complaints & Escalations.

Acceptance Criteria covered
---------------------------
✓ Admin sees all complaint details (order, user, category, description, timestamps)
✓ Admin can update the complaint status (Open → In Review → Resolved)
✓ Admin can write notes / communicate a response that the customer sees
✓ Status is persisted to CSV on every update
"""

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QScrollArea, QComboBox, QTextEdit, QMessageBox,
    QSizePolicy, QDialog,
)

from complaints import (
    COMPLAINT_STATUS_STYLES,
    load_complaints,
    update_complaint,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _badge(text, large=False):
    fg, bg = COMPLAINT_STATUS_STYLES.get(text, ("#6b7280", "#f9fafb"))
    lbl = QLabel(f"  {text}  ")
    lbl.setFixedHeight(28 if large else 24)
    lbl.setAlignment(Qt.AlignCenter)
    size = "13px" if large else "11px"
    lbl.setStyleSheet(
        f"color:{fg}; background:{bg}; border:1px solid {fg}55;"
        f" border-radius:6px; font-size:{size}; font-weight:700;"
    )
    return lbl


NEXT_STATUS = {
    "Open":      "In Review",
    "In Review": "Resolved",
    "Resolved":  None,
}

ADVANCE_BTN_LABEL = {
    "Open":      "🔍  Mark In Review",
    "In Review": "✅  Mark Resolved",
}

ADVANCE_BTN_STYLE = {
    "Open":      ("background:#f59e0b;", "background:#d97706;"),
    "In Review": ("background:#10b981;", "background:#059669;"),
}


# ─────────────────────────────────────────────────────────────────────────────
# Complaint detail dialog
# ─────────────────────────────────────────────────────────────────────────────
class ComplaintDetailDialog(QDialog):
    """Full details + action pane for a single complaint."""

    complaint_updated = pyqtSignal()   # emitted when a change is persisted

    def __init__(self, complaint, parent=None):
        super().__init__(parent)
        self.complaint = dict(complaint)   # local mutable copy
        self.setWindowTitle(f"Complaint — {self.complaint['complaint_id']}")
        self.resize(620, 560)
        self.setStyleSheet("background:#f9fafb;")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet("background:#111827; border:none;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)

        cid_lbl = QLabel(f"🎫 {self.complaint['complaint_id']}")
        cid_lbl.setFont(QFont("Arial", 14, QFont.Bold))
        cid_lbl.setStyleSheet("color:#f9fafb; background:transparent;")

        close_btn = QPushButton("✕  Close")
        close_btn.setFixedHeight(34)
        close_btn.setStyleSheet("""
            QPushButton { background:#374151; color:#d1d5db; border:none;
                border-radius:8px; padding:0 14px; font-size:13px; font-weight:600; }
            QPushButton:hover { background:#4b5563; color:white; }
        """)
        close_btn.clicked.connect(self.accept)

        hl.addWidget(cid_lbl)
        hl.addStretch()
        self._status_badge = _badge(self.complaint["status"], large=True)
        hl.addWidget(self._status_badge)
        hl.addSpacing(12)
        hl.addWidget(close_btn)
        root.addWidget(header)

        # Scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:#f9fafb; }")

        body = QWidget()
        body.setStyleSheet("background:#f9fafb;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(24, 20, 24, 24)
        body_lay.setSpacing(16)

        # Details card
        details_card = QFrame()
        details_card.setStyleSheet(
            "QFrame { background:#ffffff; border:1px solid #e5e7eb; border-radius:14px; }"
        )
        dc = QVBoxLayout(details_card)
        dc.setContentsMargins(20, 18, 20, 18)
        dc.setSpacing(10)

        def row(icon, text):
            lbl = QLabel(f"{icon}  {text}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color:#374151; font-size:13px; background:transparent;")
            return lbl

        dc.addWidget(row("📦", f"Order: {self.complaint['order_id']}  ·  {self.complaint['restaurant_name']}"))
        dc.addWidget(row("👤", f"Customer: {self.complaint['user_email']}"))
        dc.addWidget(row("🏷", f"Category: {self.complaint['category']}"))

        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet("background:#f3f4f6;")
        dc.addWidget(sep)

        desc_title = QLabel("Customer's Description")
        desc_title.setFont(QFont("Arial", 12, QFont.Bold))
        desc_title.setStyleSheet("color:#111827; background:transparent;")
        dc.addWidget(desc_title)

        desc_lbl = QLabel(self.complaint["description"])
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(
            "color:#374151; font-size:13px; background:#f9fafb;"
            " border:1px solid #e5e7eb; border-radius:8px; padding:10px 12px;"
        )
        dc.addWidget(desc_lbl)

        ts_lbl = QLabel(
            f"Submitted: {self.complaint['timestamp']}   ·   "
            f"Last updated: {self.complaint['updated_at']}"
        )
        ts_lbl.setStyleSheet("color:#9ca3af; font-size:11px; background:transparent;")
        dc.addWidget(ts_lbl)

        body_lay.addWidget(details_card)

        # Admin response card
        action_card = QFrame()
        action_card.setStyleSheet(
            "QFrame { background:#ffffff; border:1px solid #e5e7eb; border-radius:14px; }"
        )
        ac = QVBoxLayout(action_card)
        ac.setContentsMargins(20, 18, 20, 18)
        ac.setSpacing(12)

        action_title = QLabel("Admin Response & Actions")
        action_title.setFont(QFont("Arial", 13, QFont.Bold))
        action_title.setStyleSheet("color:#111827; background:transparent;")
        ac.addWidget(action_title)

        notes_lbl = QLabel("Notes / Message to customer:")
        notes_lbl.setStyleSheet(
            "color:#374151; font-size:13px; font-weight:600; background:transparent;"
        )
        ac.addWidget(notes_lbl)

        self._notes_edit = QTextEdit()
        self._notes_edit.setPlaceholderText(
            "Write a note or response for the customer (optional)…"
        )
        self._notes_edit.setFixedHeight(90)
        self._notes_edit.setPlainText(self.complaint.get("admin_notes", ""))
        self._notes_edit.setStyleSheet("""
            QTextEdit {
                border:1px solid #d1d5db; border-radius:10px;
                padding:8px 12px; font-size:13px; background:white; color:#111827;
            }
            QTextEdit:focus { border:2px solid #f0b100; }
        """)
        ac.addWidget(self._notes_edit)

        # Advance-status button (hidden when already Resolved)
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        status = self.complaint["status"]
        next_s = NEXT_STATUS.get(status)

        if next_s:
            label  = ADVANCE_BTN_LABEL[status]
            bg, hover = ADVANCE_BTN_STYLE[status]
            self._advance_btn = QPushButton(label)
            self._advance_btn.setFixedHeight(42)
            self._advance_btn.setMinimumWidth(180)
            self._advance_btn.setStyleSheet(f"""
                QPushButton {{ {bg} color:white; border:none;
                    border-radius:10px; font-size:13px; font-weight:700; padding:0 20px; }}
                QPushButton:hover {{ {hover} }}
            """)
            self._advance_btn.clicked.connect(lambda: self._advance(next_s))
            btn_row.addWidget(self._advance_btn)
        else:
            # Already resolved – show save-notes-only button
            self._advance_btn = None
            save_only = QPushButton("💾  Save Notes")
            save_only.setFixedHeight(42)
            save_only.setMinimumWidth(140)
            save_only.setStyleSheet("""
                QPushButton { background:#6366f1; color:white; border:none;
                    border-radius:10px; font-size:13px; font-weight:700; padding:0 20px; }
                QPushButton:hover { background:#4f46e5; }
            """)
            save_only.clicked.connect(self._save_notes_only)
            btn_row.addWidget(save_only)

        ac.addLayout(btn_row)
        body_lay.addWidget(action_card)
        body_lay.addStretch()

        scroll.setWidget(body)
        root.addWidget(scroll, stretch=1)

    # ── Action handlers ───────────────────────────────────────────────────────

    def _advance(self, next_status):
        notes = self._notes_edit.toPlainText().strip()
        ok = update_complaint(
            self.complaint["complaint_id"],
            status      = next_status,
            admin_notes = notes or None,
        )
        if ok:
            self.complaint["status"]      = next_status
            self.complaint["admin_notes"] = notes
            QMessageBox.information(
                self,
                "Status Updated",
                f"Complaint status is now '{next_status}'."
            )
            self.complaint_updated.emit()
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Could not update the complaint.")

    def _save_notes_only(self):
        notes = self._notes_edit.toPlainText().strip()
        ok = update_complaint(
            self.complaint["complaint_id"],
            admin_notes = notes,
        )
        if ok:
            QMessageBox.information(self, "Saved", "Admin notes have been saved.")
            self.complaint_updated.emit()
        else:
            QMessageBox.warning(self, "Error", "Could not save notes.")


# ─────────────────────────────────────────────────────────────────────────────
# Complaint row card (list view)
# ─────────────────────────────────────────────────────────────────────────────
class ComplaintRowCard(QFrame):
    open_detail = pyqtSignal(dict)

    def __init__(self, complaint, parent=None):
        super().__init__(parent)
        self.complaint = complaint
        self.setStyleSheet(
            "QFrame { background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; }"
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # Left info
        left = QVBoxLayout()
        left.setSpacing(4)

        cid_lbl = QLabel(f"🎫 {self.complaint['complaint_id']}")
        cid_lbl.setFont(QFont("Arial", 12, QFont.Bold))
        cid_lbl.setStyleSheet("color:#111827; background:transparent;")

        meta_lbl = QLabel(
            f"📦 Order #{self.complaint['order_id']}  ·  "
            f"{self.complaint['restaurant_name']}  ·  "
            f"👤 {self.complaint['user_email']}"
        )
        meta_lbl.setStyleSheet("color:#6b7280; font-size:12px; background:transparent;")
        meta_lbl.setWordWrap(True)

        cat_lbl = QLabel(f"🏷  {self.complaint['category']}")
        cat_lbl.setStyleSheet("color:#374151; font-size:12px; background:transparent;")

        ts_lbl = QLabel(f"Submitted: {self.complaint['timestamp']}")
        ts_lbl.setStyleSheet("color:#9ca3af; font-size:11px; background:transparent;")

        left.addWidget(cid_lbl)
        left.addWidget(meta_lbl)
        left.addWidget(cat_lbl)
        left.addWidget(ts_lbl)

        # Right controls
        right = QVBoxLayout()
        right.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        right.setSpacing(8)
        right.addWidget(_badge(self.complaint["status"]), alignment=Qt.AlignRight)

        view_btn = QPushButton("View Details →")
        view_btn.setFixedHeight(36)
        view_btn.setMinimumWidth(130)
        view_btn.setStyleSheet("""
            QPushButton { background:#f0b100; color:white; border:none;
                border-radius:8px; font-size:13px; font-weight:700; padding:0 16px; }
            QPushButton:hover { background:#d99f00; }
        """)
        view_btn.clicked.connect(lambda: self.open_detail.emit(self.complaint))
        right.addWidget(view_btn, alignment=Qt.AlignRight)

        layout.addLayout(left, stretch=1)
        layout.addLayout(right)


# ─────────────────────────────────────────────────────────────────────────────
# Admin complaints page
# ─────────────────────────────────────────────────────────────────────────────
class AdminComplaintsWidget(QWidget):
    """
    Full admin complaints management page.
    Intended to be embedded in the AdminDashboard QStackedWidget.
    """
    go_back = pyqtSignal()

    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data      = user_data
        self._active_filter = "All"
        self._filter_btns   = {}
        self._build_ui()

        # Auto-refresh every 5 s
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(5000)
        self.refresh()

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

        title = QLabel("Complaints & Escalations")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color:#111827;")

        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setFixedHeight(36)
        refresh_btn.setStyleSheet("""
            QPushButton { background:#f3f4f6; color:#374151; border:none;
                border-radius:8px; padding:0 16px; font-size:13px; font-weight:600; }
            QPushButton:hover { background:#e5e7eb; }
        """)
        refresh_btn.clicked.connect(self.refresh)

        hl.addWidget(back_btn)
        hl.addSpacing(12)
        hl.addWidget(title)
        hl.addStretch()
        hl.addWidget(refresh_btn)
        root.addWidget(header)

        # Stats bar
        stats_bar = QFrame()
        stats_bar.setFixedHeight(88)
        stats_bar.setStyleSheet("background:#ffffff; border-bottom:1px solid #e5e7eb;")
        stats_row = QHBoxLayout(stats_bar)
        stats_row.setContentsMargins(32, 12, 32, 12)
        stats_row.setSpacing(16)

        self._open_stat      = self._stat_card("🔴 Open",      "0", "#ef4444")
        self._review_stat    = self._stat_card("🟡 In Review", "0", "#f59e0b")
        self._resolved_stat  = self._stat_card("✅ Resolved",  "0", "#10b981")
        self._total_stat     = self._stat_card("Total",        "0", "#6366f1")

        for w in (self._open_stat, self._review_stat, self._resolved_stat, self._total_stat):
            stats_row.addWidget(w)
        stats_row.addStretch()
        root.addWidget(stats_bar)

        # Filter tabs
        filter_bar = QFrame()
        filter_bar.setFixedHeight(52)
        filter_bar.setStyleSheet("background:#ffffff; border-bottom:1px solid #e5e7eb;")
        filter_row = QHBoxLayout(filter_bar)
        filter_row.setContentsMargins(32, 0, 32, 0)
        filter_row.setSpacing(4)

        for label in ("All", "Open", "In Review", "Resolved"):
            btn = QPushButton(label)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda _c, l=label: self._set_filter(l))
            self._filter_btns[label] = btn
            filter_row.addWidget(btn)
        filter_row.addStretch()
        self._update_filter_styles()
        root.addWidget(filter_bar)

        # Scrollable list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:#f9fafb; }")

        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background:#f9fafb;")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(32, 24, 32, 24)
        self._list_layout.setSpacing(10)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_widget)
        root.addWidget(scroll, stretch=1)

    # ── Stat card helper ──────────────────────────────────────────────────────

    def _stat_card(self, label, value, color):
        frame = QFrame()
        frame.setFixedSize(160, 60)
        frame.setStyleSheet(f"""
            QFrame {{ background:{color}11; border:1px solid {color}33; border-radius:10px; }}
        """)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 8, 14, 8)
        count = QLabel(value)
        count.setFont(QFont("Arial", 20, QFont.Bold))
        count.setStyleSheet(f"color:{color}; background:transparent;")
        count.setObjectName("count")
        text = QLabel(label)
        text.setStyleSheet("color:#6b7280; font-size:12px; background:transparent;")
        text.setWordWrap(True)
        lay.addWidget(count)
        lay.addWidget(text)
        return frame

    def _update_stat(self, card, value):
        for child in card.children():
            if isinstance(child, QLabel) and child.objectName() == "count":
                child.setText(str(value))
                break

    # ── Filter helpers ────────────────────────────────────────────────────────

    def _set_filter(self, label):
        self._active_filter = label
        self._update_filter_styles()
        self.refresh()

    def _update_filter_styles(self):
        active   = """
            QPushButton { background:#f0b100; color:white; border:none;
                border-radius:8px; padding:0 16px; font-size:13px; font-weight:600; }
        """
        inactive = """
            QPushButton { background:transparent; color:#6b7280; border:none;
                border-radius:8px; padding:0 16px; font-size:13px; font-weight:600; }
            QPushButton:hover { background:#f3f4f6; color:#374151; }
        """
        for lbl, btn in self._filter_btns.items():
            btn.setStyleSheet(active if lbl == self._active_filter else inactive)

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self):
        # Clear old cards
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        all_complaints = load_complaints()
        all_complaints.sort(key=lambda c: c.get("timestamp", ""), reverse=True)

        # Update stats
        open_n     = sum(1 for c in all_complaints if c["status"] == "Open")
        review_n   = sum(1 for c in all_complaints if c["status"] == "In Review")
        resolved_n = sum(1 for c in all_complaints if c["status"] == "Resolved")

        self._update_stat(self._open_stat,     open_n)
        self._update_stat(self._review_stat,   review_n)
        self._update_stat(self._resolved_stat, resolved_n)
        self._update_stat(self._total_stat,    len(all_complaints))

        # Apply filter
        if self._active_filter != "All":
            shown = [c for c in all_complaints if c["status"] == self._active_filter]
        else:
            shown = all_complaints

        if not shown:
            msg = "No complaints yet." if not all_complaints else f"No {self._active_filter.lower()} complaints."
            empty = QLabel(msg)
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                "color:#9ca3af; font-size:15px; padding:60px; background:transparent;"
            )
            self._list_layout.insertWidget(0, empty)
            return

        for i, c in enumerate(shown):
            card = ComplaintRowCard(c)
            card.open_detail.connect(self._open_detail)
            self._list_layout.insertWidget(i, card)

    # ── Open detail dialog ────────────────────────────────────────────────────

    def _open_detail(self, complaint):
        dlg = ComplaintDetailDialog(complaint, self)
        dlg.complaint_updated.connect(self.refresh)
        dlg.exec_()