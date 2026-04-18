import csv
import json
import os
import uuid
from datetime import datetime

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QScrollArea,
    QHBoxLayout, QVBoxLayout, QStackedWidget, QLineEdit,
    QTextEdit, QButtonGroup, QRadioButton, QSizePolicy,
)

from restaurant_data import get_menu_for_restaurant

# ── CSV schema (extends main.py's existing orders_data.csv) ──────────────────
ORDERS_CSV = "orders_data.csv"
# We write these extra columns; main.py only reads order_id / restaurant_id /
# items / status – all four are present here, so the restaurant dashboard
# keeps working without any change.
_ORDER_FIELDNAMES = [
    "order_id", "restaurant_id", "restaurant_name",
    "user_email", "items", "subtotal", "delivery_fee",
    "total", "address", "payment_method", "status", "timestamp",
]


def _save_order(order: dict):
    file_exists = os.path.exists(ORDERS_CSV)
    with open(ORDERS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_ORDER_FIELDNAMES,
                                extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerow(order)


# ── Shared style snippets ─────────────────────────────────────────────────────
_BTN_PRIMARY = """
    QPushButton {
        background:#f0b100; color:white; border:none;
        border-radius:10px; font-size:13px; font-weight:700;
    }
    QPushButton:hover    { background:#d99f00; }
    QPushButton:disabled { background:#d1d5db; color:#9ca3af; }
"""
_BTN_BACK = """
    QPushButton {
        background:#f3f4f6; color:#374151; border:none;
        border-radius:8px; padding:0 14px;
        font-size:13px; font-weight:600;
    }
    QPushButton:hover { background:#e5e7eb; }
"""
_BTN_DANGER = """
    QPushButton {
        background:#fee2e2; color:#ef4444; border:none;
        border-radius:7px; font-size:12px; font-weight:600;
        padding:0 8px;
    }
    QPushButton:hover { background:#fecaca; }
"""
_INPUT = """
    QLineEdit, QTextEdit {
        border:1px solid #d1d5db; border-radius:8px;
        padding:8px 12px; font-size:13px;
        background:white; color:#111827;
    }
    QLineEdit:focus, QTextEdit:focus { border:2px solid #f0b100; }
"""
_CARD = "QFrame{background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;}"


# ── Helpers ───────────────────────────────────────────────────────────────────
def _make_header(title: str, back_label: str, back_slot) -> QFrame:
    bar = QFrame()
    bar.setFixedHeight(64)
    bar.setStyleSheet("background:#ffffff; border-bottom:1px solid #e5e7eb;")
    hl = QHBoxLayout(bar)
    hl.setContentsMargins(24, 0, 24, 0)
    hl.setSpacing(12)
    btn = QPushButton(back_label)
    btn.setFixedHeight(36)
    btn.setStyleSheet(_BTN_BACK)
    btn.clicked.connect(back_slot)
    lbl = QLabel(title)
    lbl.setFont(QFont("Arial", 15, QFont.Bold))
    lbl.setStyleSheet("color:#111827;")
    hl.addWidget(btn)
    hl.addSpacing(8)
    hl.addWidget(lbl)
    hl.addStretch()
    return bar


def _section_lbl(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        "color:#9ca3af;font-size:10px;font-weight:700;"
        "letter-spacing:1px;background:transparent;"
    )
    return lbl


def _hline() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.HLine)
    sep.setStyleSheet("color:#e5e7eb;")
    return sep


# ── Menu item row ─────────────────────────────────────────────────────────────
class _MenuItemRow(QFrame):
    """Single menu item with an Add button. Emits add_clicked(category, name, price)."""
    add_clicked = pyqtSignal(str, str, float)

    def __init__(self, category: str, item: dict, qty_in_cart: int, parent=None):
        super().__init__(parent)
        self.category = category
        self.item = item
        available = item.get("available", True)

        self.setStyleSheet(
            "QFrame{background:%s;border:1px solid %s;border-radius:12px;}"
            % (("#ffffff" if available else "#fef2f2"),
               ("#e5e7eb" if available else "#fca5a5"))
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(3)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        name_lbl = QLabel(item["name"])
        name_lbl.setFont(QFont("Arial", 12, QFont.Bold))
        name_lbl.setStyleSheet("color:#111827;border:none;background:transparent;")
        name_row.addWidget(name_lbl)

        if not available:
            badge = QLabel("Unavailable")
            badge.setStyleSheet(
                "color:#ef4444;font-size:10px;font-weight:700;"
                "border:none;background:transparent;"
            )
            name_row.addWidget(badge)

        if qty_in_cart > 0:
            in_cart = QLabel(f"{qty_in_cart} in cart")
            in_cart.setStyleSheet(
                "color:#10b981;font-size:10px;font-weight:700;"
                "background:#d1fae5;border-radius:6px;"
                "padding:1px 6px;border:none;"
            )
            name_row.addWidget(in_cart)

        name_row.addStretch()
        left.addLayout(name_row)

        desc = QLabel(item["description"])
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#6b7280;font-size:11px;border:none;background:transparent;")
        left.addWidget(desc)

        price = QLabel(f"EGP {item['price']:.2f}")
        price.setStyleSheet(
            "color:#f0b100;font-size:12px;font-weight:700;"
            "border:none;background:transparent;"
        )
        left.addWidget(price)
        layout.addLayout(left, stretch=1)

        add_btn = QPushButton("+")
        add_btn.setFixedSize(34, 34)
        add_btn.setEnabled(available)
        add_btn.setStyleSheet("""
            QPushButton{background:#f0b100;color:white;border:none;
                border-radius:17px;font-size:20px;font-weight:700;}
            QPushButton:hover   {background:#d99f00;}
            QPushButton:disabled{background:#e5e7eb;color:#9ca3af;}
        """)
        add_btn.clicked.connect(
            lambda: self.add_clicked.emit(self.category, item["name"], item["price"])
        )
        layout.addWidget(add_btn, alignment=Qt.AlignVCenter)


# ── Cart row ──────────────────────────────────────────────────────────────────
class _CartRow(QFrame):
    """One cart row with qty +/- controls and a Remove button."""
    qty_changed = pyqtSignal(str, int)   # key, new_qty  (0 = remove)

    def __init__(self, key: str, entry: dict, parent=None):
        super().__init__(parent)
        self.key   = key
        self.entry = entry
        self.qty   = entry["qty"]
        self._build()

    def _build(self):
        self.setStyleSheet(_CARD)
        self.setFixedHeight(78)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(self.entry["name"])
        name_lbl.setFont(QFont("Arial", 12, QFont.Bold))
        name_lbl.setStyleSheet("color:#111827;border:none;background:transparent;")

        self._price_lbl = QLabel()
        self._price_lbl.setStyleSheet(
            "color:#6b7280;font-size:11px;border:none;background:transparent;"
        )
        self._update_price_label()

        info.addWidget(name_lbl)
        info.addWidget(self._price_lbl)
        layout.addLayout(info, stretch=1)

        # Qty controls
        minus = QPushButton("−")
        minus.setFixedSize(28, 28)
        minus.setStyleSheet("""
            QPushButton{background:#f3f4f6;color:#374151;
                border:1px solid #e5e7eb;border-radius:6px;
                font-size:16px;font-weight:700;}
            QPushButton:hover{background:#e5e7eb;}
        """)
        minus.clicked.connect(self._decrease)

        self._qty_lbl = QLabel(str(self.qty))
        self._qty_lbl.setAlignment(Qt.AlignCenter)
        self._qty_lbl.setFixedWidth(26)
        self._qty_lbl.setFont(QFont("Arial", 12, QFont.Bold))
        self._qty_lbl.setStyleSheet("color:#111827;border:none;background:transparent;")

        plus = QPushButton("+")
        plus.setFixedSize(28, 28)
        plus.setStyleSheet("""
            QPushButton{background:#f0b100;color:white;border:none;
                border-radius:6px;font-size:16px;font-weight:700;}
            QPushButton:hover{background:#d99f00;}
        """)
        plus.clicked.connect(self._increase)

        remove = QPushButton("Remove")
        remove.setFixedHeight(28)
        remove.setStyleSheet(_BTN_DANGER)
        remove.clicked.connect(lambda: self.qty_changed.emit(self.key, 0))

        ctrl = QHBoxLayout()
        ctrl.setSpacing(4)
        ctrl.addWidget(minus)
        ctrl.addWidget(self._qty_lbl)
        ctrl.addWidget(plus)
        ctrl.addSpacing(6)
        ctrl.addWidget(remove)
        layout.addLayout(ctrl)

    def _update_price_label(self):
        self._price_lbl.setText(
            f"EGP {self.entry['price']:.2f} each  ·  "
            f"Subtotal EGP {self.entry['price'] * self.qty:.2f}"
        )

    def _increase(self):
        self.qty += 1
        self._qty_lbl.setText(str(self.qty))
        self._update_price_label()
        self.qty_changed.emit(self.key, self.qty)

    def _decrease(self):
        self.qty = max(0, self.qty - 1)
        if self.qty == 0:
            self.qty_changed.emit(self.key, 0)
        else:
            self._qty_lbl.setText(str(self.qty))
            self._update_price_label()
            self.qty_changed.emit(self.key, self.qty)


# ── Main widget ───────────────────────────────────────────────────────────────
class CartOrderWidget(QWidget):
    """
    Embedded QWidget covering the full Cart → Checkout → Success flow.

    Signals
    -------
    go_back_to_nearby      user pressed Back from the menu/restaurant page
    go_back_to_restaurant  user pressed Back from the cart page
    order_confirmed        emitted with the completed order dict
    """
    go_back_to_nearby     = pyqtSignal()
    go_back_to_restaurant = pyqtSignal()
    order_confirmed       = pyqtSignal(dict)

    _PAGE_MENU     = 0
    _PAGE_CART     = 1
    _PAGE_CHECKOUT = 2
    _PAGE_SUCCESS  = 3

    def __init__(self, restaurant: dict, user_data: dict, parent=None):
        super().__init__(parent)
        self.restaurant = restaurant
        self.user_data  = user_data
        self.menu_data  = get_menu_for_restaurant(restaurant["id"])
        # cart: { "Category|Item Name": {name, price, category, qty} }
        self.cart: dict[str, dict] = {}

        self._stack = QStackedWidget(self)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._stack)

        self._stack.addWidget(self._build_menu_page())      # 0
        self._stack.addWidget(self._build_cart_page())      # 1
        self._stack.addWidget(self._build_checkout_page())  # 2
        self._stack.addWidget(self._build_success_page())   # 3

    # ── Private helpers ───────────────────────────────────────────────────────
    def _subtotal(self)     -> float: return sum(e["price"] * e["qty"] for e in self.cart.values())
    def _delivery_fee(self) -> float: return float(self.restaurant.get("fee", 0))
    def _total(self)        -> float: return self._subtotal() + self._delivery_fee()
    def _cart_count(self)   -> int:   return sum(e["qty"] for e in self.cart.values())
    def _go_to(self, page: int):      self._stack.setCurrentIndex(page)

    # ── PAGE 0 – Menu / Restaurant Details ───────────────────────────────────
    def _build_menu_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Store header label reference so load_restaurant can update it
        self._menu_header_lbl = QLabel(f"🍽  {self.restaurant['name']}")
        self._menu_header_lbl.setFont(QFont("Arial", 15, QFont.Bold))
        self._menu_header_lbl.setStyleSheet("color:#111827;")
        header = _make_header(
            f"🍽  {self.restaurant['name']}",
            "← Restaurants",
            self.go_back_to_nearby.emit,
        )
        # Replace the generic title label in header with our stored reference
        _hdr_layout = header.layout()
        for i in range(_hdr_layout.count()):
            w = _hdr_layout.itemAt(i).widget()
            if isinstance(w, QLabel):
                self._menu_header_lbl = w
                break
        layout.addWidget(header)

        # Info strip (matches restaurant_details.py style)
        strip = QFrame()
        strip.setStyleSheet("background:#fffbeb;border-bottom:1px solid #fde68a;")
        sl = QHBoxLayout(strip)
        sl.setContentsMargins(24, 8, 24, 8)
        self._menu_meta_lbl = QLabel(
            f"⭐ {self.restaurant.get('rating', '—')}  ·  "
            f"🕐 ~{self.restaurant.get('delivery_time', '?')} min  ·  "
            f"📍 {self.restaurant.get('distance_km', '?')} km away  ·  "
            f"💳 EGP {self.restaurant.get('fee', 0):.0f} delivery  ·  "
            f"{self.restaurant.get('category', '')}"
        )
        self._menu_meta_lbl.setStyleSheet("color:#92400e;font-size:12px;font-weight:600;")
        sl.addWidget(self._menu_meta_lbl)
        layout.addWidget(strip)

        # Scrollable menu
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:#f9fafb;}")
        container = QWidget()
        container.setStyleSheet("background:#f9fafb;")
        self._menu_layout = QVBoxLayout(container)
        self._menu_layout.setContentsMargins(24, 16, 24, 100)
        self._menu_layout.setSpacing(10)
        self._render_menu_items()
        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

        # Sticky cart bar
        bar = QFrame()
        bar.setStyleSheet("QFrame{background:#ffffff;border-top:1px solid #e5e7eb;}")
        bar.setFixedHeight(72)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 12, 24, 12)
        self._view_cart_btn = QPushButton("🛒  View Cart")
        self._view_cart_btn.setFixedHeight(46)
        self._view_cart_btn.setEnabled(False)
        self._view_cart_btn.setStyleSheet(_BTN_PRIMARY)
        self._view_cart_btn.clicked.connect(lambda: self._go_to(self._PAGE_CART))
        bl.addWidget(self._view_cart_btn)
        layout.addWidget(bar)
        return page

    def _render_menu_items(self):
        while self._menu_layout.count():
            item = self._menu_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        categories: dict = self.menu_data.get("categories", {})
        for cat_name, items in categories.items():
            self._menu_layout.addWidget(_section_lbl(cat_name))
            for item in items:
                key = f"{cat_name}|{item['name']}"
                qty = self.cart[key]["qty"] if key in self.cart else 0
                row = _MenuItemRow(cat_name, item, qty)
                row.add_clicked.connect(self._on_add_item)
                self._menu_layout.addWidget(row)
            self._menu_layout.addSpacing(4)
        self._menu_layout.addStretch()

    def _on_add_item(self, category: str, name: str, price: float):
        key = f"{category}|{name}"
        if key in self.cart:
            self.cart[key]["qty"] += 1
        else:
            self.cart[key] = {"name": name, "price": price,
                               "category": category, "qty": 1}
        self._refresh_all()

    def _refresh_all(self):
        count = self._cart_count()
        self._view_cart_btn.setEnabled(count > 0)
        self._view_cart_btn.setText(
            (f"🛒  View Cart ({count} item{'s' if count != 1 else ''})  ·  "
             f"EGP {self._total():.2f}")
            if count > 0 else "🛒  View Cart"
        )
        self._render_menu_items()
        self._render_cart_rows()
        self._update_totals()

    # ── PAGE 1 – Cart ─────────────────────────────────────────────────────────
    def _build_cart_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(_make_header(
            "🛒  Your Cart",
            "← Menu",
            lambda: self._go_to(self._PAGE_MENU),
        ))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:#f9fafb;}")
        container = QWidget()
        container.setStyleSheet("background:#f9fafb;")
        self._cart_rows_layout = QVBoxLayout(container)
        self._cart_rows_layout.setContentsMargins(24, 16, 24, 16)
        self._cart_rows_layout.setSpacing(10)
        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

        # Totals + checkout button
        panel = QFrame()
        panel.setStyleSheet("QFrame{background:#ffffff;border-top:1px solid #e5e7eb;}")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(24, 14, 24, 14)
        pl.setSpacing(6)

        def _tot_row(label_text: str, bold=False):
            row = QHBoxLayout()
            l = QLabel(label_text)
            r = QLabel("EGP 0.00")
            s = ("color:#111827;font-size:14px;font-weight:700;"
                 if bold else "color:#6b7280;font-size:13px;")
            l.setStyleSheet(s); r.setStyleSheet(s)
            row.addWidget(l); row.addStretch(); row.addWidget(r)
            pl.addLayout(row)
            return r

        self._sub_lbl   = _tot_row("Subtotal")
        self._fee_lbl   = _tot_row("Delivery fee")
        pl.addWidget(_hline())
        self._total_lbl = _tot_row("Total", bold=True)

        self._checkout_btn = QPushButton("Proceed to Checkout →")
        self._checkout_btn.setFixedHeight(46)
        self._checkout_btn.setEnabled(False)
        self._checkout_btn.setStyleSheet(_BTN_PRIMARY)
        self._checkout_btn.clicked.connect(self._open_checkout)
        pl.addSpacing(6)
        pl.addWidget(self._checkout_btn)
        layout.addWidget(panel)
        return page

    def _render_cart_rows(self):
        while self._cart_rows_layout.count():
            item = self._cart_rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.cart:
            empty = QLabel("Your cart is empty.\nGo back to the menu to add items.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setWordWrap(True)
            empty.setStyleSheet("color:#9ca3af;font-size:14px;padding:40px;")
            self._cart_rows_layout.addWidget(empty)
            self._checkout_btn.setEnabled(False)
            return

        self._checkout_btn.setEnabled(True)
        for key, entry in self.cart.items():
            row = _CartRow(key, entry)
            row.qty_changed.connect(self._on_qty_changed)
            self._cart_rows_layout.addWidget(row)
        self._cart_rows_layout.addStretch()

    def _on_qty_changed(self, key: str, new_qty: int):
        if new_qty == 0:
            self.cart.pop(key, None)
        elif key in self.cart:
            self.cart[key]["qty"] = new_qty
        self._refresh_all()

    def _update_totals(self):
        sub = self._subtotal()
        fee = self._delivery_fee()
        self._sub_lbl.setText(f"EGP {sub:.2f}")
        self._fee_lbl.setText(f"EGP {fee:.2f}")
        self._total_lbl.setText(f"EGP {sub + fee:.2f}")

    def _open_checkout(self):
        # Sync summary labels before showing checkout page
        sub = self._subtotal()
        fee = self._delivery_fee()
        self._chk_sub.setText(f"EGP {sub:.2f}")
        self._chk_fee.setText(f"EGP {fee:.2f}")
        self._chk_total.setText(f"EGP {sub + fee:.2f}")
        self._go_to(self._PAGE_CHECKOUT)

    # ── PAGE 2 – Checkout ─────────────────────────────────────────────────────
    def _build_checkout_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(_make_header(
            "Checkout",
            "← Cart",
            lambda: self._go_to(self._PAGE_CART),
        ))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:#f9fafb;}")
        inner = QWidget()
        inner.setStyleSheet("background:#f9fafb;")
        il = QVBoxLayout(inner)
        il.setContentsMargins(24, 20, 24, 20)
        il.setSpacing(16)

        # ── Address ──
        addr_card = QFrame()
        addr_card.setStyleSheet(_CARD)
        acl = QVBoxLayout(addr_card)
        acl.setContentsMargins(16, 14, 16, 14)
        acl.setSpacing(10)
        addr_title = QLabel("📍  Delivery Address")
        addr_title.setFont(QFont("Arial", 12, QFont.Bold))
        addr_title.setStyleSheet("color:#111827;background:transparent;")
        acl.addWidget(addr_title)

        self._street = QLineEdit()
        self._street.setPlaceholderText("Street address  (e.g. 14 Tahrir Square)")
        self._street.setStyleSheet(_INPUT)

        row2 = QHBoxLayout()
        self._city = QLineEdit()
        self._city.setPlaceholderText("City")
        self._city.setStyleSheet(_INPUT)
        self._apt = QLineEdit()
        self._apt.setPlaceholderText("Apt / Floor  (optional)")
        self._apt.setStyleSheet(_INPUT)
        row2.addWidget(self._city)
        row2.addWidget(self._apt)

        self._notes = QTextEdit()
        self._notes.setPlaceholderText("Delivery notes  (e.g. Ring bell twice…)")
        self._notes.setFixedHeight(68)
        self._notes.setStyleSheet(_INPUT)

        acl.addWidget(self._street)
        acl.addLayout(row2)
        acl.addWidget(self._notes)
        il.addWidget(addr_card)

        # ── Payment ──
        pay_card = QFrame()
        pay_card.setStyleSheet(_CARD)
        pcl = QVBoxLayout(pay_card)
        pcl.setContentsMargins(16, 14, 16, 14)
        pcl.setSpacing(10)
        pay_title = QLabel("💳  Payment Method")
        pay_title.setFont(QFont("Arial", 12, QFont.Bold))
        pay_title.setStyleSheet("color:#111827;background:transparent;")
        pcl.addWidget(pay_title)

        self._pay_group = QButtonGroup(self)
        self._cash_rb = QRadioButton("💵  Cash on delivery")
        self._card_rb = QRadioButton("💳  Credit / Debit card")
        self._cash_rb.setChecked(True)
        for rb in (self._cash_rb, self._card_rb):
            rb.setStyleSheet("color:#374151;font-size:13px;")
            self._pay_group.addButton(rb)
            pcl.addWidget(rb)

        # Card fields
        self._card_fields = QFrame()
        self._card_fields.setStyleSheet("background:transparent;")
        cfl = QVBoxLayout(self._card_fields)
        cfl.setContentsMargins(0, 0, 0, 0)
        cfl.setSpacing(8)
        self._card_num = QLineEdit()
        self._card_num.setPlaceholderText("Card number  (e.g. 1234-5678-9012-3456)")
        self._card_num.setMaxLength(19)
        self._card_num.setStyleSheet(_INPUT)
        self._card_num.textChanged.connect(self._fmt_card_num)
        exp_cvv = QHBoxLayout()
        self._card_exp = QLineEdit()
        self._card_exp.setPlaceholderText("MM/YY")
        self._card_exp.setMaxLength(5)
        self._card_exp.setStyleSheet(_INPUT)
        self._card_exp.textChanged.connect(self._fmt_card_exp)
        self._card_cvv = QLineEdit()
        self._card_cvv.setPlaceholderText("CVV")
        self._card_cvv.setMaxLength(3)
        self._card_cvv.setEchoMode(QLineEdit.Password)
        self._card_cvv.setStyleSheet(_INPUT)
        exp_cvv.addWidget(self._card_exp)
        exp_cvv.addWidget(self._card_cvv)
        cfl.addWidget(self._card_num)
        cfl.addLayout(exp_cvv)
        self._card_fields.hide()
        self._card_rb.toggled.connect(
            lambda checked: self._card_fields.setVisible(checked)
        )
        pcl.addWidget(self._card_fields)
        il.addWidget(pay_card)

        # ── Order summary ──
        sum_card = QFrame()
        sum_card.setStyleSheet(_CARD)
        scl = QVBoxLayout(sum_card)
        scl.setContentsMargins(16, 14, 16, 14)
        scl.setSpacing(6)
        sum_title = QLabel("🧾  Order Summary")
        sum_title.setFont(QFont("Arial", 12, QFont.Bold))
        sum_title.setStyleSheet("color:#111827;background:transparent;")
        scl.addWidget(sum_title)

        def _sum_row(label):
            row = QHBoxLayout()
            l = QLabel(label)
            r = QLabel("EGP 0.00")
            l.setStyleSheet("color:#6b7280;font-size:13px;background:transparent;")
            r.setStyleSheet("color:#6b7280;font-size:13px;background:transparent;")
            row.addWidget(l); row.addStretch(); row.addWidget(r)
            scl.addLayout(row)
            return r

        self._chk_sub   = _sum_row("Subtotal")
        self._chk_fee   = _sum_row("Delivery fee")
        scl.addWidget(_hline())

        tot_row = QHBoxLayout()
        tl = QLabel("Total"); tl.setFont(QFont("Arial", 13, QFont.Bold))
        tl.setStyleSheet("color:#111827;background:transparent;")
        self._chk_total = QLabel("EGP 0.00")
        self._chk_total.setFont(QFont("Arial", 13, QFont.Bold))
        self._chk_total.setStyleSheet("color:#111827;background:transparent;")
        tot_row.addWidget(tl); tot_row.addStretch(); tot_row.addWidget(self._chk_total)
        scl.addLayout(tot_row)
        il.addWidget(sum_card)

        # Error + confirm
        self._err_lbl = QLabel()
        self._err_lbl.setWordWrap(True)
        self._err_lbl.setStyleSheet(
            "color:#991b1b;font-size:12px;background:#fee2e2;"
            "border-radius:8px;padding:8px 12px;"
        )
        self._err_lbl.hide()
        il.addWidget(self._err_lbl)

        confirm_btn = QPushButton("✔  Confirm Order")
        confirm_btn.setFixedHeight(48)
        confirm_btn.setStyleSheet(_BTN_PRIMARY)
        confirm_btn.clicked.connect(self._confirm_order)
        il.addWidget(confirm_btn)
        il.addStretch()

        scroll.setWidget(inner)
        layout.addWidget(scroll, stretch=1)
        return page

    # ── Card field auto-formatters ────────────────────────────────────────────
    def _fmt_card_num(self, text: str):
        """Insert a hyphen after every 4 digits automatically."""
        self._card_num.blockSignals(True)
        digits = text.replace("-", "")[:16]
        parts = [digits[i:i+4] for i in range(0, len(digits), 4)]
        formatted = "-".join(parts)
        self._card_num.setText(formatted)
        self._card_num.setCursorPosition(len(formatted))
        self._card_num.blockSignals(False)

    def _fmt_card_exp(self, text: str):
        """Auto-insert '/' after 2 valid month digits."""
        self._card_exp.blockSignals(True)
        digits = text.replace("/", "")[:4]
        if len(digits) >= 2:
            month = digits[:2]
            if month.isdigit() and 1 <= int(month) <= 12:
                year_part = digits[2:]
                formatted = month + ("/" + year_part if year_part else "/")
            else:
                formatted = digits
        else:
            formatted = digits
        self._card_exp.setText(formatted)
        self._card_exp.setCursorPosition(len(formatted))
        self._card_exp.blockSignals(False)

    def _confirm_order(self):
        street = self._street.text().strip()
        city   = self._city.text().strip()

        if not street or not city:
            self._err_lbl.setText("⚠  Please enter your street address and city.")
            self._err_lbl.show()
            return

        # Street and city must contain only letters, spaces, and common punctuation
        import re
        if not re.fullmatch(r"[A-Za-z\u0600-\u06FF .,\-']+", street):
            self._err_lbl.setText("⚠  Street address must contain letters only (no numbers or special characters).")
            self._err_lbl.show()
            return
        if not re.fullmatch(r"[A-Za-z\u0600-\u06FF .,\-']+", city):
            self._err_lbl.setText("⚠  City must contain letters only.")
            self._err_lbl.show()
            return

        pay = "cash" if self._cash_rb.isChecked() else "card"
        if pay == "card":
            num = self._card_num.text().replace("-", "")   # strip hyphens before length check
            exp = self._card_exp.text()
            cvv = self._card_cvv.text()
            if len(num) < 16 or len(cvv) < 3:
                self._err_lbl.setText("⚠  Please enter a valid 16-digit card number and 3-digit CVV.")
                self._err_lbl.show()
                return
            # CVV checking
            if not re.fullmatch(r"[0-9]{3,4}", cvv):
                self._err_lbl.setText("⚠  CVV must contain digits only (no letters or special characters).")
                self._err_lbl.show()
                return
            # Validate expiry format and date
            if not re.fullmatch(r"(0[1-9]|1[0-2])/[0-9]{2}", exp):
                self._err_lbl.setText("⚠  Expiry must be MM/YY with a valid month (01–12).")
                self._err_lbl.show()
                return
            # Check expiry is beyond yesterday
            from datetime import date
            today = date.today()
            mm, yy = int(exp[:2]), int(exp[3:])
            full_year = 2000 + yy
            # Card is valid through the last day of the expiry month
            import calendar
            last_day = calendar.monthrange(full_year, mm)[1]
            card_expiry = date(full_year, mm, last_day)
            yesterday = date(today.year, today.month, today.day - 1) if today.day > 1 else date(
                today.year if today.month > 1 else today.year - 1,
                today.month - 1 if today.month > 1 else 12,
                calendar.monthrange(
                    today.year if today.month > 1 else today.year - 1,
                    today.month - 1 if today.month > 1 else 12
                )[1]
            )
            if card_expiry <= yesterday:
                self._err_lbl.setText("⚠  Your card has expired. Please use a valid card.")
                self._err_lbl.show()
                return

        self._err_lbl.hide()

        sub = self._subtotal()
        fee = self._delivery_fee()
        items_str = "; ".join(
            f"{v['qty']}x {v['name']} (EGP {v['price']:.2f})"
            for v in self.cart.values()
        )
        apt   = self._apt.text().strip()
        notes = self._notes.toPlainText().strip()
        address = ", ".join(filter(None, [street, apt, city]))
        if notes:
            address += f" — {notes}"

        order = {
            "order_id":        "WAS-" + str(uuid.uuid4())[:8].upper(),
            "restaurant_id":   self.restaurant["id"],
            "restaurant_name": self.restaurant["name"],
            "user_email":      self.user_data.get("email", ""),
            "items":           items_str,
            "subtotal":        f"{sub:.2f}",
            "delivery_fee":    f"{fee:.2f}",
            "total":           f"{sub + fee:.2f}",
            "address":         address,
            "payment_method":  pay,
            "status":          "Pending",
            "timestamp":       datetime.now().isoformat(timespec="seconds"),
        }
        _save_order(order)
        self._populate_success(order)
        self._go_to(self._PAGE_SUCCESS)
        self.order_confirmed.emit(order)

    # ── PAGE 3 – Success ──────────────────────────────────────────────────────
    def _build_success_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background:#f9fafb;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)
        layout.addStretch()

        tick = QLabel("✓")
        tick.setAlignment(Qt.AlignCenter)
        tick.setFont(QFont("Arial", 36, QFont.Bold))
        tick.setFixedSize(80, 80)
        tick.setStyleSheet(
            "background:#d1fae5;color:#059669;border-radius:40px;"
        )
        layout.addWidget(tick, alignment=Qt.AlignHCenter)

        self._succ_title = QLabel("Order Placed!")
        self._succ_title.setFont(QFont("Arial", 22, QFont.Bold))
        self._succ_title.setStyleSheet("color:#111827;")
        self._succ_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._succ_title)

        self._succ_sub = QLabel()
        self._succ_sub.setAlignment(Qt.AlignCenter)
        self._succ_sub.setWordWrap(True)
        self._succ_sub.setStyleSheet("color:#6b7280;font-size:13px;")
        layout.addWidget(self._succ_sub)

        # Wrapper holds the summary card; we replace its child on each order
        self._succ_card_wrapper = QFrame()
        self._succ_card_wrapper.setStyleSheet("background:transparent;border:none;")
        self._succ_card_wrapper_layout = QVBoxLayout(self._succ_card_wrapper)
        self._succ_card_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        self._succ_card_wrapper_layout.setSpacing(0)
        layout.addWidget(self._succ_card_wrapper)

        browse_btn = QPushButton("Browse More Restaurants")
        browse_btn.setFixedHeight(46)
        browse_btn.setStyleSheet(_BTN_PRIMARY)
        browse_btn.clicked.connect(self._start_new_order)
        layout.addWidget(browse_btn)

        layout.addStretch()
        return page

    def _populate_success(self, order: dict):
        self._succ_sub.setText(
            f"Your order has been sent to {self.restaurant['name']}.\n"
            f"Order ID: {order['order_id']}  ·  "
            f"Payment: {'Cash on delivery' if order['payment_method'] == 'cash' else 'Card'}"
        )

        # ── Fully replace the card widget so no old layouts/widgets linger ──
        # Remove and immediately destroy every child of the wrapper
        while self._succ_card_wrapper_layout.count():
            child = self._succ_card_wrapper_layout.takeAt(0)
            w = child.widget()
            if w:
                w.setParent(None)   # unparent first so deleteLater fires immediately
                w.deleteLater()

        # Build a brand-new card frame from scratch
        card = QFrame()
        card.setStyleSheet(_CARD)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(6)

        # Restaurant name + status pill row
        top_w = QWidget()
        top_w.setStyleSheet("background:transparent;")
        top_l = QHBoxLayout(top_w)
        top_l.setContentsMargins(0, 0, 0, 0)
        top_l.setSpacing(0)
        r_lbl = QLabel(self.restaurant["name"])
        r_lbl.setFont(QFont("Arial", 13, QFont.Bold))
        r_lbl.setStyleSheet("color:#111827;background:transparent;")
        pill = QLabel("● Pending")
        pill.setStyleSheet(
            "color:#f0b100;background:#fef9ec;border-radius:10px;"
            "font-size:11px;font-weight:700;padding:2px 10px;border:none;"
        )
        top_l.addWidget(r_lbl)
        top_l.addStretch()
        top_l.addWidget(pill)
        cl.addWidget(top_w)
        cl.addWidget(_hline())

        for entry in self.cart.values():
            row_w = QWidget()
            row_w.setStyleSheet("background:transparent;")
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(0)
            il = QLabel(f"{entry['qty']}×  {entry['name']}")
            il.setStyleSheet("color:#374151;font-size:12px;background:transparent;")
            ir = QLabel(f"EGP {entry['price'] * entry['qty']:.2f}")
            ir.setStyleSheet("color:#374151;font-size:12px;background:transparent;")
            row_l.addWidget(il)
            row_l.addStretch()
            row_l.addWidget(ir)
            cl.addWidget(row_w)

        cl.addWidget(_hline())

        tot_w = QWidget()
        tot_w.setStyleSheet("background:transparent;")
        tot_l = QHBoxLayout(tot_w)
        tot_l.setContentsMargins(0, 0, 0, 0)
        tot_l.setSpacing(0)
        tl = QLabel("Total")
        tl.setFont(QFont("Arial", 13, QFont.Bold))
        tl.setStyleSheet("color:#111827;background:transparent;")
        tr = QLabel(f"EGP {order['total']}")
        tr.setFont(QFont("Arial", 13, QFont.Bold))
        tr.setStyleSheet("color:#111827;background:transparent;")
        tot_l.addWidget(tl)
        tot_l.addStretch()
        tot_l.addWidget(tr)
        cl.addWidget(tot_w)

        self._succ_card_wrapper_layout.addWidget(card)

    def _start_new_order(self):
        self.cart.clear()
        self._refresh_all()
        self.go_back_to_nearby.emit()

    # ── Public API ────────────────────────────────────────────────────────────
    def load_restaurant(self, restaurant: dict):
        """Switch to a different restaurant (resets cart and all form state)."""
        self.restaurant = restaurant
        self.menu_data  = get_menu_for_restaurant(restaurant["id"])
        self.cart.clear()

        # Reset checkout form fields so a new order starts clean
        self._street.clear()
        self._city.clear()
        self._apt.clear()
        self._notes.clear()
        self._cash_rb.setChecked(True)
        self._card_num.blockSignals(True)
        self._card_num.clear()
        self._card_num.blockSignals(False)
        self._card_exp.blockSignals(True)
        self._card_exp.clear()
        self._card_exp.blockSignals(False)
        self._card_cvv.clear()
        self._err_lbl.hide()

        # Update menu page header and info strip for the new restaurant
        self._menu_header_lbl.setText(f"🍽  {restaurant['name']}")
        self._menu_meta_lbl.setText(
            f"⭐ {restaurant.get('rating', '—')}  ·  "
            f"🕐 ~{restaurant.get('delivery_time', '?')} min  ·  "
            f"📍 {restaurant.get('distance_km', '?')} km away  ·  "
            f"💳 EGP {restaurant.get('fee', 0):.0f} delivery  ·  "
            f"{restaurant.get('category', '')}"
        )

        self._refresh_all()
        self._go_to(self._PAGE_MENU)


