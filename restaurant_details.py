from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QScrollArea, QSizePolicy
)

from restaurant_data import get_menu_for_restaurant


class MenuItemCard(QFrame):
    def __init__(self, item, parent=None):
        super().__init__(parent)

        available = item.get("available", True)
        border_color = "#e5e7eb" if available else "#fca5a5"
        bg_color = "#ffffff" if available else "#fef2f2"

        self.setStyleSheet(f"""
            QFrame {{
                background: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(4)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        name_lbl = QLabel(item["name"])
        name_lbl.setFont(QFont("Arial", 12, QFont.Bold))
        name_lbl.setStyleSheet("color: #111827; border: none; background: transparent;")
        name_row.addWidget(name_lbl)

        status_text = "Available" if available else "Unavailable"
        status_color = "#10b981" if available else "#ef4444"
        status_badge = QLabel(status_text)
        status_badge.setStyleSheet(f"""
            color: {status_color};
            font-size: 11px;
            font-weight: 700;
            border: none;
            background: transparent;
        """)
        name_row.addWidget(status_badge)
        name_row.addStretch()

        desc_lbl = QLabel(item["description"])
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #6b7280; font-size: 12px; border: none; background: transparent;")

        left.addLayout(name_row)
        left.addWidget(desc_lbl)

        price_lbl = QLabel(f"EGP {item['price']:.2f}")
        price_lbl.setFont(QFont("Arial", 11, QFont.Bold))
        price_lbl.setStyleSheet("color: #f0b100; border: none; background: transparent;")

        layout.addLayout(left, stretch=1)
        layout.addWidget(price_lbl, alignment=Qt.AlignVCenter)


class MenuCategorySection(QFrame):
    def __init__(self, category_name, items, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 14px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel(category_name)
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #111827; border: none; background: transparent;")
        layout.addWidget(title)

        for item in items:
            layout.addWidget(MenuItemCard(item))


class RestaurantDetailsWidget(QWidget):
    go_back  = pyqtSignal()
    # NEW: emits the full restaurant dict when the user taps Order Now
    order_now = pyqtSignal(dict)

    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data  = user_data
        self.restaurant = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet("background: #ffffff; border-bottom: 1px solid #e5e7eb;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)

        back_btn = QPushButton("← Back")
        back_btn.setFixedHeight(36)
        back_btn.setStyleSheet("""
            QPushButton {
                background: #f3f4f6;
                color: #374151;
                border: none;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover { background: #e5e7eb; }
        """)
        back_btn.clicked.connect(self.go_back.emit)

        self.title_lbl = QLabel("Restaurant Details")
        self.title_lbl.setFont(QFont("Arial", 16, QFont.Bold))
        self.title_lbl.setStyleSheet("color: #111827;")

        user_lbl = QLabel(f"👤 {self.user_data.get('full_name', 'Customer')}")
        user_lbl.setStyleSheet("color: #6b7280; font-size: 13px;")

        hl.addWidget(back_btn)
        hl.addSpacing(12)
        hl.addWidget(self.title_lbl)
        hl.addStretch()
        hl.addWidget(user_lbl)

        root.addWidget(header)

        # Scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f9fafb; }")

        self.content = QWidget()
        self.content.setStyleSheet("background: #f9fafb;")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(24, 20, 24, 24)
        self.content_layout.setSpacing(16)

        scroll.setWidget(self.content)
        root.addWidget(scroll)

    def set_restaurant(self, restaurant):
        self.restaurant = restaurant
        self.title_lbl.setText(f"🍽  {restaurant['name']}")
        self._render_restaurant()

    def _clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _render_restaurant(self):
        self._clear_content()

        if not self.restaurant:
            empty = QLabel("No restaurant selected.")
            empty.setStyleSheet("color: #6b7280; font-size: 14px;")
            self.content_layout.addWidget(empty)
            return

        r = self.restaurant
        menu_data = get_menu_for_restaurant(r["id"])

        # ── Restaurant details card ──
        details_card = QFrame()
        details_card.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
            }
        """)
        details_layout = QVBoxLayout(details_card)
        details_layout.setContentsMargins(20, 20, 20, 20)
        details_layout.setSpacing(8)

        name_lbl = QLabel(r["name"])
        name_lbl.setFont(QFont("Arial", 20, QFont.Bold))
        name_lbl.setStyleSheet("color: #111827;")

        address_lbl = QLabel(f"📍 {r.get('address', 'No address available')}")
        address_lbl.setStyleSheet("color: #6b7280; font-size: 13px;")

        category_lbl = QLabel(f"Category: {r.get('category', 'Restaurant')}")
        category_lbl.setStyleSheet("color: #374151; font-size: 13px;")

        meta_lbl = QLabel(
            f"⭐ Rating: {r.get('rating', 0)}    ·    "
            f"🕐 Delivery Time: ~{r.get('delivery_time', 0)} min    ·    "
            f"💳 Delivery Fee: EGP {r.get('fee', 0):.0f}"
        )
        meta_lbl.setWordWrap(True)
        meta_lbl.setStyleSheet("color: #111827; font-size: 13px; font-weight: 600;")

        details_layout.addWidget(name_lbl)
        details_layout.addWidget(address_lbl)
        details_layout.addWidget(category_lbl)
        details_layout.addWidget(meta_lbl)

        self.content_layout.addWidget(details_card)

        # ── Order Now button ──
        order_btn = QPushButton("🛒  Order Now")
        order_btn.setFixedHeight(48)
        order_btn.setStyleSheet("""
            QPushButton {
                background: #f0b100;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover { background: #d99f00; }
        """)
        order_btn.clicked.connect(lambda: self.order_now.emit(self.restaurant))
        self.content_layout.addWidget(order_btn)

        # ── Menu ──
        menu_title = QLabel("Menu")
        menu_title.setFont(QFont("Arial", 18, QFont.Bold))
        menu_title.setStyleSheet("color: #111827;")
        self.content_layout.addWidget(menu_title)

        categories = menu_data.get("categories", {})
        for category_name, items in categories.items():
            self.content_layout.addWidget(MenuCategorySection(category_name, items))

        self.content_layout.addStretch()