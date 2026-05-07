import csv
import json
import os
import sys
from datetime import datetime
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QLabel, QPushButton,
    QLineEdit, QHBoxLayout, QVBoxLayout, QFrame, QMessageBox,
    QCheckBox, QStackedWidget, QComboBox, QScrollArea, QSizePolicy, QDialog
)
from nearby_restaurants import NearbyRestaurantsWidget
from restaurant_details import RestaurantDetailsWidget
from cart_order import CartOrderWidget
from restaurant_data import get_menu_for_restaurant, set_item_availability
from complaint_widget import ReportIssueWidget
from admin_complaints import AdminComplaintsWidget

SPLASH_PATH = "splashscreen.png"
SIDE_IMAGE_PATH = "sidescreen.png"
CSV_PATH = "users_data.csv"
CSV_HEADERS = ["full_name", "email", "phone", "password", "role"]
ORDERS_CSV = "orders_data.csv"
ORDERS_HEADERS = [
    "order_id", "restaurant_id", "restaurant_name",
    "user_email", "items", "subtotal", "delivery_fee",
    "total", "address", "payment_method", "status", "timestamp", "updated_at"
]
SESSION_PATH = "session.json"
RESTAURANT_OWNERS_CSV = "restaurant_owners.csv"
RESTAURANT_OWNERS_HEADERS = ["email", "restaurant_id", "restaurant_name"]
DEFAULT_RESTAURANT_OWNERS = [
    {
        "email": "nour.restaurant@example.com",
        "restaurant_id": "R01",
        "restaurant_name": "Koshary El Tahrir",
    }
]

ORDER_STATUS_STYLES = {
    "Pending": ("#f59e0b", "#fffbeb"),
    "Accepted": ("#10b981", "#ecfdf5"),
    "Preparing": ("#3b82f6", "#eff6ff"),
    "Ready for Pickup": ("#8b5cf6", "#f5f3ff"),
    "Rejected": ("#ef4444", "#fef2f2"),
}

VALID_STATUS_TRANSITIONS = {
    "Pending": {"Accepted", "Rejected"},
    "Accepted": {"Preparing"},
    "Preparing": {"Ready for Pickup"},
}


def current_timestamp():
    return datetime.now().isoformat(timespec="seconds")

DUMMY_USERS = [
    {
        "full_name": "Mariam Adel",
        "email": "mariam@example.com",
        "phone": "+201001234567",
        "password": "pass123",
        "role": "User",
    },
    {
        "full_name": "Omar Hassan",
        "email": "omar.driver@example.com",
        "phone": "+201015556677",
        "password": "driver123",
        "role": "Driver",
    },
    {
        "full_name": "Nour Kitchen",
        "email": "nour.restaurant@example.com",
        "phone": "+201028889911",
        "password": "rest123",
        "role": "Restaurant",
    },
]


def ensure_csv_exists():
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_HEADERS)
            writer.writeheader()
            writer.writerows(DUMMY_USERS)

    if not os.path.exists(ORDERS_CSV):
        with open(ORDERS_CSV, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=ORDERS_HEADERS)
            writer.writeheader()

    if not os.path.exists(RESTAURANT_OWNERS_CSV):
        with open(RESTAURANT_OWNERS_CSV, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=RESTAURANT_OWNERS_HEADERS)
            writer.writeheader()
            writer.writerows(DEFAULT_RESTAURANT_OWNERS)


def load_users():
    ensure_csv_exists()
    users = []

    with open(CSV_PATH, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            normalized = {
                "full_name": row.get("full_name", "").strip(),
                "email": row.get("email", "").strip(),
                "phone": row.get("phone", "").strip(),
                "password": row.get("password", "").strip(),
                "role": row.get("role", "User").strip() or "User",
            }
            if normalized["email"]:
                users.append(normalized)

    return users


def find_user_by_email(email):
    target = email.strip().lower()
    for user in load_users():
        if user["email"].lower() == target:
            return user
    return None


def append_user(user_data):
    ensure_csv_exists()
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_HEADERS)
        writer.writerow(user_data)

def save_session(user_data):
    """Save logged-in user to session file (Remember Me)."""
    with open(SESSION_PATH, "w", encoding="utf-8") as f:
        json.dump({"email": user_data["email"]}, f)


def load_session():
    """Return user_data if a valid saved session exists, else None."""
    if not os.path.exists(SESSION_PATH):
        return None
    try:
        with open(SESSION_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return find_user_by_email(data.get("email", ""))
    except Exception:
        return None


def clear_session():
    """Delete the saved session file."""
    if os.path.exists(SESSION_PATH):
        os.remove(SESSION_PATH)


def load_orders():
    ensure_csv_exists()
    orders = []
    if not os.path.exists(ORDERS_CSV):
        return orders

    with open(ORDERS_CSV, "r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader, None)  # Skip header row

        for row in reader:
            if not row:
                continue

            # Legacy Sprint 1 rows had only: order_id, restaurant_id, items, status
            if len(row) == 4:
                order_dict = {
                    "order_id": row[0],
                    "restaurant_id": row[1],
                    "restaurant_name": "Legacy Restaurant",
                    "user_email": "N/A",
                    "items": row[2],
                    "subtotal": "0",
                    "delivery_fee": "0",
                    "total": "0",
                    "address": "N/A",
                    "payment_method": "N/A",
                    "status": row[3],
                    "timestamp": "N/A",
                    "updated_at": "N/A",
                }
            else:
                order_dict = {}
                for i, header in enumerate(ORDERS_HEADERS):
                    order_dict[header] = row[i].strip() if i < len(row) else ""

                if not order_dict.get("updated_at"):
                    order_dict["updated_at"] = order_dict.get("timestamp", "N/A") or "N/A"

            order_dict["status"] = order_dict.get("status", "Pending").strip() or "Pending"
            orders.append(order_dict)

    return orders


def get_order_by_id(order_id):
    for order in load_orders():
        if order.get("order_id") == str(order_id):
            return order
    return None


def update_order_status_csv(order_id, new_status):
    orders = load_orders()
    found = False

    for order in orders:
        if order.get("order_id") == str(order_id):
            order["status"] = new_status
            order["updated_at"] = current_timestamp()
            found = True
            break

    if not found:
        return False

    with open(ORDERS_CSV, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=ORDERS_HEADERS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(orders)

    return True


def load_restaurant_owners():
    ensure_csv_exists()
    owners = []

    if not os.path.exists(RESTAURANT_OWNERS_CSV):
        return owners

    with open(RESTAURANT_OWNERS_CSV, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            email = row.get("email", "").strip().lower()
            restaurant_id = row.get("restaurant_id", "").strip()
            restaurant_name = row.get("restaurant_name", "").strip()
            if email and restaurant_id:
                owners.append({
                    "email": email,
                    "restaurant_id": restaurant_id,
                    "restaurant_name": restaurant_name,
                })

    return owners


def get_restaurant_owner_record(email):
    target = email.strip().lower()
    for owner in load_restaurant_owners():
        if owner["email"] == target:
            return owner
    return None



class CustomerOrdersWidget(QWidget):
    """Customer order tracking page. Refreshes CSV data periodically."""
    go_back = pyqtSignal()

    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self._build_ui()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh_orders)
        self._refresh_timer.start(3000)
        self.refresh_orders()

    def _build_ui(self):
        self.setStyleSheet("background: #f9fafb;")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet("background: #ffffff; border-bottom: 1px solid #e5e7eb;")
        h = QHBoxLayout(header)
        h.setContentsMargins(24, 0, 24, 0)

        back_btn = QPushButton("← Dashboard")
        back_btn.setFixedHeight(36)
        back_btn.setStyleSheet("""
            QPushButton { background: #f3f4f6; color: #374151; border: none;
                border-radius: 8px; padding: 0 14px; font-size: 13px; font-weight: 600; }
            QPushButton:hover { background: #e5e7eb; }
        """)
        back_btn.clicked.connect(self.go_back.emit)

        title = QLabel("Track My Orders")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #111827;")

        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setFixedHeight(36)
        refresh_btn.setStyleSheet("""
            QPushButton { background: #f0b100; color: white; border: none;
                border-radius: 8px; padding: 0 16px; font-size: 13px; font-weight: 600; }
            QPushButton:hover { background: #d99f00; }
        """)
        refresh_btn.clicked.connect(self.refresh_orders)

        h.addWidget(back_btn)
        h.addSpacing(12)
        h.addWidget(title)
        h.addStretch()
        h.addWidget(refresh_btn)
        root.addWidget(header)

        info = QLabel("Order statuses refresh automatically every 3 seconds.")
        info.setStyleSheet(
            "background: #fffbeb; color: #92400e; border-bottom: 1px solid #fde68a;"
            " padding: 10px 24px; font-size: 12px;"
        )
        root.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f9fafb; }")

        self._orders_widget = QWidget()
        self._orders_widget.setStyleSheet("background: #f9fafb;")
        self._orders_layout = QVBoxLayout(self._orders_widget)
        self._orders_layout.setContentsMargins(32, 24, 32, 24)
        self._orders_layout.setSpacing(12)
        self._orders_layout.addStretch()

        scroll.setWidget(self._orders_widget)
        root.addWidget(scroll, stretch=1)

    def refresh_orders(self):
        while self._orders_layout.count() > 1:
            item = self._orders_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        email = self.user_data.get("email", "").strip().lower()
        orders = [
            order for order in load_orders()
            if order.get("user_email", "").strip().lower() == email
        ]
        orders.reverse()

        if not orders:
            empty = QLabel("You do not have any orders yet.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                "color: #9ca3af; font-size: 15px; padding: 60px; background: transparent;"
            )
            self._orders_layout.insertWidget(0, empty)
            return

        for i, order in enumerate(orders):
            self._orders_layout.insertWidget(i, self._build_order_card(order))

    def _build_order_card(self, order):
        status = order.get("status", "Pending")
        fg, bg = ORDER_STATUS_STYLES.get(status, ("#6b7280", "#f9fafb"))

        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; }"
        )
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel(f"Order #{order.get('order_id', 'N/A')}")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #111827; background: transparent;")

        badge = QLabel(f"  {status}  ")
        badge.setFixedHeight(26)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            f"color: {fg}; background: {bg}; border: 1px solid {fg}55;"
            " border-radius: 6px; font-size: 12px; font-weight: 700;"
        )

        top.addWidget(title)
        top.addStretch()
        top.addWidget(badge)
        layout.addLayout(top)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #f3f4f6;")
        layout.addWidget(sep)

        details = QVBoxLayout()
        details.setSpacing(6)

        restaurant = QLabel(f"🏪  {order.get('restaurant_name', 'N/A')}")
        restaurant.setStyleSheet("color: #374151; font-size: 13px; background: transparent;")

        items = QLabel(f"🍽  {order.get('items', 'N/A')}")
        items.setWordWrap(True)
        items.setStyleSheet("color: #374151; font-size: 13px; background: transparent;")

        total = QLabel(f"💰  Total: EGP {order.get('total', '—')}")
        total.setStyleSheet("color: #111827; font-size: 13px; font-weight: 700; background: transparent;")

        updated = QLabel(f"Last update: {order.get('updated_at') or order.get('timestamp', 'N/A')}")
        updated.setStyleSheet("color: #9ca3af; font-size: 11px; background: transparent;")

        details.addWidget(restaurant)
        details.addWidget(items)
        details.addWidget(total)
        details.addWidget(updated)
        layout.addLayout(details)

        return card


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wasaly")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        pixmap = QPixmap(SPLASH_PATH)
        self.setFixedSize(400, 650)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.background_label = QLabel()
        self.background_label.setAlignment(Qt.AlignCenter)

        if pixmap.isNull():
            self.setStyleSheet("background-color: #f0b100;")
            self.background_label.setText("splashscreen.png not found")
            self.background_label.setStyleSheet(
                "color: white; font-size: 24px; font-weight: bold;"
            )
        else:
            scaled = pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            self.background_label.setPixmap(scaled)
            self.background_label.setScaledContents(True)

        layout.addWidget(self.background_label)

    def resizeEvent(self, event):
        pixmap = QPixmap(SPLASH_PATH)
        if not pixmap.isNull() and hasattr(self, "background_label"):
            scaled = pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            self.background_label.setPixmap(scaled)
        super().resizeEvent(event)


class RoleWindow(QMainWindow):
    """Customer Dashboard with same-window navigation using QStackedWidget."""
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        role = user_data.get("role", "User")
        name = user_data.get("full_name", "User")

        self.setWindowTitle(f"Wasaly – Customer Dashboard")
        self.resize(900, 620)
        self.setStyleSheet("background: #f9fafb;")

        # Stacked widget: page 0 = dashboard, page 1 = nearby restaurants
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Build dashboard page
        dashboard_page = QWidget()
        layout = QVBoxLayout(dashboard_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet("background: #ffffff; border-bottom: 1px solid #e5e7eb;")
        header.setFixedHeight(64)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(32, 0, 32, 0)

        logo_img = QLabel()
        logo_pixmap = QPixmap("logo.png")
        if not logo_pixmap.isNull():
            logo_img.setPixmap(logo_pixmap.scaled(120, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo_img.setText("Wasaly")
            logo_img.setFont(QFont("Arial", 18, QFont.Bold))
            logo_img.setStyleSheet("color: #f0b100;")
        logo_lbl = logo_img

        user_lbl = QLabel(f"👤 {name}")
        user_lbl.setStyleSheet("color: #6b7280; font-size: 13px;")

        logout_btn = QPushButton("Logout")
        logout_btn.setFixedHeight(32)
        logout_btn.setStyleSheet("""
            QPushButton {
                background: #fee2e2; color: #ef4444; border: none;
                border-radius: 8px; padding: 0 14px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: #fecaca; }
        """)
        logout_btn.clicked.connect(self._logout)

        h_layout.addWidget(logo_lbl)
        h_layout.addStretch()
        h_layout.addWidget(user_lbl)
        h_layout.addSpacing(10)
        h_layout.addWidget(logout_btn)
        layout.addWidget(header)

        # Body
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(40, 36, 40, 40)
        body_layout.setSpacing(20)

        welcome = QLabel(f"Welcome back, {name.split()[0]}! 👋")
        welcome.setFont(QFont("Arial", 22, QFont.Bold))
        welcome.setStyleSheet("color: #111827;")

        subtitle = QLabel("What would you like to do today?")
        subtitle.setStyleSheet("color: #6b7280; font-size: 14px;")

        body_layout.addWidget(welcome)
        body_layout.addWidget(subtitle)
        body_layout.addSpacing(8)

        # Feature cards grid
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        # ── Discover Nearby card (YOUR FEATURE – active) ──
        # ── Shared card style ──
        CARD_H = 160
        CARD_MARGINS = (16, 14, 16, 14)
        ICON_SIZE = 18
        TITLE_SIZE = 12

        nearby_card = QFrame()
        nearby_card.setStyleSheet("QFrame { background: #f0b100; border-radius: 14px; }")
        nearby_card.setFixedHeight(CARD_H)
        nc_layout = QVBoxLayout(nearby_card)
        nc_layout.setContentsMargins(*CARD_MARGINS)
        nc_layout.setSpacing(6)

        nc_icon = QLabel("📍")
        nc_icon.setFont(QFont("Arial", ICON_SIZE))
        nc_icon.setStyleSheet("background: transparent;")

        nc_title = QLabel("Discover Nearby Restaurants")
        nc_title.setFont(QFont("Arial", TITLE_SIZE, QFont.Bold))
        nc_title.setWordWrap(True)
        nc_title.setStyleSheet("color: #ffffff; background: transparent;")

        nc_btn = QPushButton("Open →")
        nc_btn.setFixedHeight(32)
        nc_btn.setStyleSheet("""
            QPushButton {
                background: white; color: #f0b100; border: none;
                border-radius: 8px; font-size: 12px; font-weight: 700;
            }
            QPushButton:hover { background: #fffbeb; }
        """)
        nc_btn.clicked.connect(self._open_nearby_restaurants)

        nc_layout.addWidget(nc_icon)
        nc_layout.addWidget(nc_title)
        nc_layout.addStretch()
        nc_layout.addWidget(nc_btn)

        # ── Placeholder cards for future sprints ──
        def _placeholder_card(icon, title, sprint):
            card = QFrame()
            card.setStyleSheet(
                "QFrame { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px; }"
            )
            card.setFixedHeight(CARD_H)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(*CARD_MARGINS)
            cl.setSpacing(6)

            lbl_icon = QLabel(icon)
            lbl_icon.setFont(QFont("Arial", ICON_SIZE))
            lbl_icon.setStyleSheet("background: transparent;")

            lbl_title = QLabel(title)
            lbl_title.setFont(QFont("Arial", TITLE_SIZE, QFont.Bold))
            lbl_title.setStyleSheet("color: #374151; background: transparent;")
            lbl_title.setWordWrap(True)

            lbl_soon = QLabel(f"Coming in {sprint}")
            lbl_soon.setStyleSheet("color: #9ca3af; font-size: 11px; background: transparent;")

            cl.addWidget(lbl_icon)
            cl.addWidget(lbl_title)
            cl.addStretch()
            cl.addWidget(lbl_soon)
            return card

        cart_card = _placeholder_card("🛒", "My Cart & Checkout", "Sprint 2")

        orders_card = QFrame()
        orders_card.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px; }"
        )
        orders_card.setFixedHeight(CARD_H)
        oc_layout = QVBoxLayout(orders_card)
        oc_layout.setContentsMargins(*CARD_MARGINS)
        oc_layout.setSpacing(6)

        oc_icon = QLabel("📦")
        oc_icon.setFont(QFont("Arial", ICON_SIZE))
        oc_icon.setStyleSheet("background: transparent;")

        oc_title = QLabel("Track My Orders")
        oc_title.setFont(QFont("Arial", TITLE_SIZE, QFont.Bold))
        oc_title.setWordWrap(True)
        oc_title.setStyleSheet("color: #374151; background: transparent;")

        oc_btn = QPushButton("Open →")
        oc_btn.setFixedHeight(32)
        oc_btn.setStyleSheet("""
            QPushButton {
                background: #f0b100; color: white; border: none;
                border-radius: 8px; font-size: 12px; font-weight: 700;
            }
            QPushButton:hover { background: #d99f00; }
        """)
        oc_btn.clicked.connect(self._open_order_tracking)

        oc_layout.addWidget(oc_icon)
        oc_layout.addWidget(oc_title)
        oc_layout.addStretch()
        oc_layout.addWidget(oc_btn)

        reviews_card = _placeholder_card("⭐", "Ratings & Reviews", "Sprint 3")

        # ── Report Issue card ──
        issue_card = QFrame()
        issue_card.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #fca5a5; border-radius: 14px; }"
        )
        issue_card.setFixedHeight(CARD_H)
        ic_layout = QVBoxLayout(issue_card)
        ic_layout.setContentsMargins(*CARD_MARGINS)
        ic_layout.setSpacing(6)

        ic_icon = QLabel("🚨")
        ic_icon.setFont(QFont("Arial", ICON_SIZE))
        ic_icon.setStyleSheet("background: transparent;")

        ic_title = QLabel("Report an Issue")
        ic_title.setFont(QFont("Arial", TITLE_SIZE, QFont.Bold))
        ic_title.setWordWrap(True)
        ic_title.setStyleSheet("color: #374151; background: transparent;")

        ic_btn = QPushButton("Open →")
        ic_btn.setFixedHeight(32)
        ic_btn.setStyleSheet("""
            QPushButton {
                background: #ef4444; color: white; border: none;
                border-radius: 8px; font-size: 12px; font-weight: 700;
            }
            QPushButton:hover { background: #dc2626; }
        """)
        ic_btn.clicked.connect(self._open_report_issue)

        ic_layout.addWidget(ic_icon)
        ic_layout.addWidget(ic_title)
        ic_layout.addStretch()
        ic_layout.addWidget(ic_btn)

        cards_layout.addWidget(nearby_card)
        cards_layout.addWidget(cart_card)
        cards_layout.addWidget(orders_card)
        cards_layout.addWidget(issue_card)
        cards_layout.addWidget(reviews_card)

        body_layout.addLayout(cards_layout)
        body_layout.addStretch()
        layout.addWidget(body)

        self.stack.addWidget(dashboard_page)   # index 0

        # Build nearby restaurants page
        self.nearby_widget = NearbyRestaurantsWidget(self.user_data)
        self.nearby_widget.go_back.connect(lambda: self.stack.setCurrentIndex(0))
        self.nearby_widget.restaurant_selected.connect(self._open_restaurant_details)
        self.stack.addWidget(self.nearby_widget)  # index 1
        self.restaurant_details_widget = RestaurantDetailsWidget(self.user_data)
        self.restaurant_details_widget.go_back.connect(lambda: self.stack.setCurrentIndex(1))
        self.stack.addWidget(self.restaurant_details_widget)  # index 2

        # Cart + Checkout widget (index 3)
        _placeholder = {"id": "R01", "name": "", "fee": 0,
                        "rating": 0, "delivery_time": 0,
                        "distance_km": 0, "category": ""}
        self.cart_widget = CartOrderWidget(_placeholder, self.user_data)
        self.cart_widget.go_back_to_nearby.connect(lambda: self.stack.setCurrentIndex(1))
        self.cart_widget.go_back_to_restaurant.connect(lambda: self.stack.setCurrentIndex(2))
        self.stack.addWidget(self.cart_widget)  # index 3

        # Customer order tracking widget (index 4)
        self.orders_widget = CustomerOrdersWidget(self.user_data)
        self.orders_widget.go_back.connect(lambda: self.stack.setCurrentIndex(0))
        self.stack.addWidget(self.orders_widget)  # index 4

        # Report Issue widget (index 5)
        user_orders = [
            o for o in load_orders()
            if o.get("user_email", "").strip().lower() ==
               self.user_data.get("email", "").strip().lower()
        ]
        self.report_issue_widget = ReportIssueWidget(self.user_data, user_orders)
        self.report_issue_widget.go_back.connect(lambda: self.stack.setCurrentIndex(0))
        self.stack.addWidget(self.report_issue_widget)  # index 5

        # Connect restaurant details "Order Now" -> cart
        self.restaurant_details_widget.order_now.connect(self._open_cart)

    def _logout(self):
        clear_session()
        from PyQt5.QtWidgets import QApplication
        # Restart auth window
        self.auth_window = AuthWindow()
        center_window(self.auth_window)
        self.auth_window.show()
        self.close()

    def _open_nearby_restaurants(self):
        self.stack.setCurrentIndex(1)

    def _open_restaurant_details(self, restaurant):
        self.restaurant_details_widget.set_restaurant(restaurant)
        self.stack.setCurrentIndex(2)

    def _open_cart(self, restaurant):
        self.cart_widget.load_restaurant(restaurant)
        self.stack.setCurrentIndex(3)

    def _open_order_tracking(self):
        self.orders_widget.refresh_orders()
        self.stack.setCurrentIndex(4)

    def _open_report_issue(self):
        # Refresh the user's orders list each time the page is opened
        user_orders = [
            o for o in load_orders()
            if o.get("user_email", "").strip().lower() ==
               self.user_data.get("email", "").strip().lower()
        ]
        self.report_issue_widget.orders = user_orders
        self.report_issue_widget._populate_orders()
        self.report_issue_widget.refresh_past_complaints()
        self.stack.setCurrentIndex(5)

class MenuAvailabilityDialog(QDialog):
    """Restaurant-side dialog for toggling item availability."""

    def __init__(self, owner_record, user_data, parent=None):
        super().__init__(parent)
        self.owner_record = owner_record
        self.user_data = user_data
        self.restaurant_id = owner_record["restaurant_id"]
        self.restaurant_name = owner_record.get("restaurant_name") or self.restaurant_id
        self.setWindowTitle("Manage Menu Availability")
        self.resize(820, 620)
        self.setStyleSheet("background: #f9fafb;")
        self._build_ui()
        self.refresh_menu()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet("background: #ffffff; border-bottom: 1px solid #e5e7eb;")
        h = QHBoxLayout(header)
        h.setContentsMargins(24, 0, 24, 0)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Manage Menu Availability")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #111827; background: transparent;")
        subtitle = QLabel(f"{self.restaurant_name}  ·  {self.restaurant_id}")
        subtitle.setStyleSheet("color: #6b7280; font-size: 12px; background: transparent;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setFixedHeight(36)
        refresh_btn.setStyleSheet("""
            QPushButton { background: #f3f4f6; color: #374151; border: none;
                border-radius: 8px; padding: 0 16px; font-size: 13px; font-weight: 600; }
            QPushButton:hover { background: #e5e7eb; }
        """)
        refresh_btn.clicked.connect(self.refresh_menu)

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet("""
            QPushButton { background: #111827; color: white; border: none;
                border-radius: 8px; padding: 0 16px; font-size: 13px; font-weight: 600; }
            QPushButton:hover { background: #374151; }
        """)
        close_btn.clicked.connect(self.accept)

        h.addLayout(title_box)
        h.addStretch()
        h.addWidget(refresh_btn)
        h.addWidget(close_btn)
        root.addWidget(header)

        info = QLabel("Toggle item availability here. Customer menus and checkout will use the latest saved status.")
        info.setStyleSheet(
            "background: #fffbeb; color: #92400e; border-bottom: 1px solid #fde68a;"
            " padding: 10px 24px; font-size: 12px;"
        )
        root.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f9fafb; }")

        self._content = QWidget()
        self._content.setStyleSheet("background: #f9fafb;")
        self._menu_layout = QVBoxLayout(self._content)
        self._menu_layout.setContentsMargins(24, 18, 24, 24)
        self._menu_layout.setSpacing(12)
        self._menu_layout.addStretch()

        scroll.setWidget(self._content)
        root.addWidget(scroll, stretch=1)

    def refresh_menu(self):
        while self._menu_layout.count() > 1:
            item = self._menu_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        menu_data = get_menu_for_restaurant(self.restaurant_id)
        categories = menu_data.get("categories", {})

        if not categories:
            empty = QLabel("No menu items found for this restaurant.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #9ca3af; font-size: 14px; padding: 60px;")
            self._menu_layout.insertWidget(0, empty)
            return

        insert_index = 0
        for category, items in categories.items():
            section = QLabel(category.upper())
            section.setStyleSheet(
                "color: #9ca3af; font-size: 11px; font-weight: 800;"
                " letter-spacing: 1px; background: transparent; margin-top: 8px;"
            )
            self._menu_layout.insertWidget(insert_index, section)
            insert_index += 1

            for menu_item in items:
                card = self._build_item_card(category, menu_item)
                self._menu_layout.insertWidget(insert_index, card)
                insert_index += 1

    def _build_item_card(self, category, item):
        available = bool(item.get("available", True))
        fg = "#10b981" if available else "#ef4444"
        bg = "#ecfdf5" if available else "#fef2f2"
        border = "#e5e7eb" if available else "#fca5a5"

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: #ffffff; border: 1px solid {border}; border-radius: 12px; }}"
        )
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(4)

        name = QLabel(item.get("name", "Unnamed item"))
        name.setFont(QFont("Arial", 13, QFont.Bold))
        name.setStyleSheet("color: #111827; background: transparent; border: none;")

        desc = QLabel(item.get("description", ""))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #6b7280; font-size: 12px; background: transparent; border: none;")

        price = QLabel(f"EGP {float(item.get('price', 0)):.2f}")
        price.setStyleSheet("color: #f0b100; font-size: 12px; font-weight: 700; background: transparent; border: none;")

        left.addWidget(name)
        if desc.text():
            left.addWidget(desc)
        left.addWidget(price)

        badge = QLabel("  Available  " if available else "  Unavailable  ")
        badge.setFixedHeight(26)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            f"color: {fg}; background: {bg}; border: 1px solid {fg}55;"
            " border-radius: 6px; font-size: 12px; font-weight: 700;"
        )

        btn = QPushButton("Mark Unavailable" if available else "Mark Available")
        btn.setFixedHeight(38)
        btn.setMinimumWidth(160)
        btn.setStyleSheet("""
            QPushButton { background: #f0b100; color: white; border: none;
                border-radius: 8px; padding: 0 16px; font-size: 13px; font-weight: 700; }
            QPushButton:hover { background: #d99f00; }
        """)
        btn.clicked.connect(
            lambda _checked=False, c=category, n=item.get("name", ""), new_value=(not available):
                self._toggle_item(c, n, new_value)
        )

        layout.addLayout(left, stretch=1)
        layout.addWidget(badge, alignment=Qt.AlignVCenter)
        layout.addWidget(btn, alignment=Qt.AlignVCenter)
        return card

    def _toggle_item(self, category, item_name, available):
        if not item_name:
            return

        set_item_availability(
            self.restaurant_id,
            category,
            item_name,
            available,
            self.user_data.get("email", ""),
        )
        QMessageBox.information(
            self,
            "Availability Updated",
            f"{item_name} is now {'Available' if available else 'Unavailable'}."
        )
        self.refresh_menu()


class RestaurantDashboard(QMainWindow):
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        name = user_data.get("full_name", "Restaurant Owner")
        self.owner_record = get_restaurant_owner_record(user_data.get("email", ""))
        self.restaurant_id = self.owner_record["restaurant_id"] if self.owner_record else None
        self.restaurant_name = (
            self.owner_record.get("restaurant_name") if self.owner_record else "No linked restaurant"
        )
        self._active_filter = "All"
        self._filter_btns = {}

        self.setWindowTitle("Wasaly — Restaurant Portal")
        self.resize(1100, 720)
        self.setStyleSheet("background: #f9fafb;")

        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("QFrame { background: #111827; }")
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(24, 32, 24, 32)
        sb.setSpacing(0)

        logo_lbl = QLabel("Wasaly")
        logo_lbl.setFont(QFont("Arial", 22, QFont.Bold))
        logo_lbl.setStyleSheet("color: #f0b100; background: transparent;")
        sb.addWidget(logo_lbl)

        portal_lbl = QLabel("Restaurant Portal")
        portal_lbl.setStyleSheet("color: #6b7280; font-size: 12px; background: transparent;")
        sb.addWidget(portal_lbl)
        sb.addSpacing(32)

        avatar_lbl = QLabel(name[0].upper() if name else "R")
        avatar_lbl.setFixedSize(56, 56)
        avatar_lbl.setAlignment(Qt.AlignCenter)
        avatar_lbl.setStyleSheet(
            "background: #f0b100; color: white; border-radius: 28px;"
            " font-size: 22px; font-weight: bold;"
        )
        sb.addWidget(avatar_lbl, alignment=Qt.AlignLeft)
        sb.addSpacing(12)

        name_lbl = QLabel(name)
        name_lbl.setFont(QFont("Arial", 14, QFont.Bold))
        name_lbl.setStyleSheet("color: #f9fafb; background: transparent;")
        name_lbl.setWordWrap(True)
        sb.addWidget(name_lbl)

        email_lbl = QLabel(user_data.get("email", ""))
        email_lbl.setStyleSheet("color: #9ca3af; font-size: 11px; background: transparent;")
        email_lbl.setWordWrap(True)
        sb.addWidget(email_lbl)

        restaurant_lbl = QLabel(f"🏪 {self.restaurant_name}")
        restaurant_lbl.setStyleSheet("color: #f0b100; font-size: 11px; font-weight: 700; background: transparent;")
        restaurant_lbl.setWordWrap(True)
        sb.addWidget(restaurant_lbl)
        sb.addSpacing(24)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: #374151;")
        sb.addWidget(div)
        sb.addSpacing(20)

        online_lbl = QLabel("● Online")
        online_lbl.setStyleSheet(
            "color: #10b981; font-size: 12px; font-weight: 600; background: transparent;"
        )
        sb.addWidget(online_lbl)
        sb.addStretch()

        logout_btn = QPushButton("Sign Out")
        logout_btn.setFixedHeight(40)
        logout_btn.setStyleSheet("""
            QPushButton {
                background: #1f2937; color: #9ca3af;
                border: 1px solid #374151; border-radius: 8px;
                font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background: #374151; color: white; }
        """)
        logout_btn.clicked.connect(self._logout)
        sb.addWidget(logout_btn)

        root.addWidget(sidebar)

        # ── Main area ─────────────────────────────────────────────────────────
        main_area = QWidget()
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top bar
        topbar = QFrame()
        topbar.setFixedHeight(64)
        topbar.setStyleSheet("background: #ffffff; border-bottom: 1px solid #e5e7eb;")
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(32, 0, 32, 0)

        page_title = QLabel("Order Management")
        page_title.setFont(QFont("Arial", 18, QFont.Bold))
        page_title.setStyleSheet("color: #111827;")

        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setFixedHeight(36)
        refresh_btn.setStyleSheet("""
            QPushButton { background: #f3f4f6; color: #374151; border: none;
                border-radius: 8px; padding: 0 16px; font-size: 13px; font-weight: 600; }
            QPushButton:hover { background: #e5e7eb; }
        """)
        refresh_btn.clicked.connect(self.refresh_orders)

        manage_menu_btn = QPushButton("🍽  Manage Menu Availability")
        manage_menu_btn.setFixedHeight(36)
        manage_menu_btn.setEnabled(self.owner_record is not None)
        manage_menu_btn.setStyleSheet("""
            QPushButton { background: #f0b100; color: white; border: none;
                border-radius: 8px; padding: 0 16px; font-size: 13px; font-weight: 700; }
            QPushButton:hover { background: #d99f00; }
            QPushButton:disabled { background: #e5e7eb; color: #9ca3af; }
        """)
        manage_menu_btn.clicked.connect(self._open_menu_availability)

        tb.addWidget(page_title)
        tb.addStretch()
        tb.addWidget(manage_menu_btn)
        tb.addSpacing(8)
        tb.addWidget(refresh_btn)
        main_layout.addWidget(topbar)

        # Stats bar
        stats_bar = QFrame()
        stats_bar.setFixedHeight(88)
        stats_bar.setStyleSheet("background: #ffffff; border-bottom: 1px solid #e5e7eb;")
        stats_row = QHBoxLayout(stats_bar)
        stats_row.setContentsMargins(32, 12, 32, 12)
        stats_row.setSpacing(16)

        self.pending_stat   = self._stat_card("⏳ Pending",      "0", "#f59e0b")
        self.accepted_stat  = self._stat_card("✅ Accepted",     "0", "#10b981")
        self.preparing_stat = self._stat_card("👨‍🍳 Preparing",   "0", "#3b82f6")
        self.ready_stat     = self._stat_card("📦 Ready",        "0", "#8b5cf6")
        self.total_stat     = self._stat_card("Total",          "0", "#6366f1")

        for w in (self.pending_stat, self.accepted_stat, self.preparing_stat, self.ready_stat, self.total_stat):
            stats_row.addWidget(w)
        stats_row.addStretch()
        main_layout.addWidget(stats_bar)

        # Filter tabs
        filter_bar = QFrame()
        filter_bar.setFixedHeight(52)
        filter_bar.setStyleSheet("background: #ffffff; border-bottom: 1px solid #e5e7eb;")
        filter_row = QHBoxLayout(filter_bar)
        filter_row.setContentsMargins(32, 0, 32, 0)
        filter_row.setSpacing(4)

        for label in ("All", "Pending", "Accepted", "Preparing", "Ready for Pickup", "Rejected"):
            btn = QPushButton(label)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda _checked, l=label: self._set_filter(l))
            self._filter_btns[label] = btn
            filter_row.addWidget(btn)
        filter_row.addStretch()
        self._update_filter_styles()
        main_layout.addWidget(filter_bar)

        # Scrollable order list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f9fafb; }")

        self._orders_widget = QWidget()
        self._orders_widget.setStyleSheet("background: #f9fafb;")
        self._orders_layout = QVBoxLayout(self._orders_widget)
        self._orders_layout.setContentsMargins(32, 24, 32, 24)
        self._orders_layout.setSpacing(12)
        self._orders_layout.addStretch()

        scroll.setWidget(self._orders_widget)
        main_layout.addWidget(scroll, stretch=1)

        root.addWidget(main_area, stretch=1)

        self.refresh_orders()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _owned_orders(self):
        if not self.restaurant_id:
            return []
        return [
            order for order in load_orders()
            if order.get("restaurant_id", "").strip() == self.restaurant_id
        ]

    def _open_menu_availability(self):
        if not self.owner_record:
            QMessageBox.warning(
                self,
                "No Linked Restaurant",
                "No restaurant is linked to this account. Please contact the admin."
            )
            return
        dialog = MenuAvailabilityDialog(self.owner_record, self.user_data, self)
        dialog.exec_()

    def _stat_card(self, label, value, color):
        frame = QFrame()
        frame.setFixedSize(140, 60)
        frame.setStyleSheet(f"""
            QFrame {{
                background: {color}11;
                border: 1px solid {color}33;
                border-radius: 10px;
            }}
        """)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 8, 14, 8)

        count_lbl = QLabel(value)
        count_lbl.setFont(QFont("Arial", 20, QFont.Bold))
        count_lbl.setStyleSheet(f"color: {color}; background: transparent;")
        count_lbl.setObjectName("count")

        text_lbl = QLabel(label)
        text_lbl.setStyleSheet("color: #6b7280; font-size: 12px; background: transparent;")
        text_lbl.setWordWrap(True)

        lay.addWidget(count_lbl)
        lay.addWidget(text_lbl)
        return frame

    def _update_stat(self, card, value):
        for child in card.children():
            if isinstance(child, QLabel) and child.objectName() == "count":
                child.setText(str(value))
                break

    def _update_filter_styles(self):
        active = """
            QPushButton { background: #f0b100; color: white; border: none;
                border-radius: 8px; padding: 0 16px; font-size: 13px; font-weight: 600; }
        """
        inactive = """
            QPushButton { background: transparent; color: #6b7280; border: none;
                border-radius: 8px; padding: 0 16px; font-size: 13px; font-weight: 600; }
            QPushButton:hover { background: #f3f4f6; color: #374151; }
        """
        for label, btn in self._filter_btns.items():
            btn.setStyleSheet(active if label == self._active_filter else inactive)

    def _set_filter(self, label):
        self._active_filter = label
        self._update_filter_styles()
        self.refresh_orders()

    def _logout(self):
        clear_session()
        self.auth_window = AuthWindow()
        center_window(self.auth_window)
        self.auth_window.show()
        self.close()

    # ── Order rendering ───────────────────────────────────────────────────────

    def refresh_orders(self):
        while self._orders_layout.count() > 1:
            item = self._orders_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        all_orders = self._owned_orders()

        if not self.restaurant_id:
            for card in (self.pending_stat, self.accepted_stat, self.preparing_stat, self.ready_stat, self.total_stat):
                self._update_stat(card, 0)
            empty = QLabel("No restaurant is linked to this account. Please contact the admin.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                "color: #ef4444; font-size: 15px; padding: 60px;"
                " background: transparent;"
            )
            self._orders_layout.insertWidget(0, empty)
            return

        pending   = sum(1 for o in all_orders if o["status"] == "Pending")
        accepted  = sum(1 for o in all_orders if o["status"] == "Accepted")
        preparing = sum(1 for o in all_orders if o["status"] == "Preparing")
        ready     = sum(1 for o in all_orders if o["status"] == "Ready for Pickup")

        self._update_stat(self.pending_stat,   pending)
        self._update_stat(self.accepted_stat,  accepted)
        self._update_stat(self.preparing_stat, preparing)
        self._update_stat(self.ready_stat,     ready)
        self._update_stat(self.total_stat,     len(all_orders))

        if self._active_filter != "All":
            orders = [o for o in all_orders if o["status"] == self._active_filter]
        else:
            orders = all_orders

        if not orders:
            msg = "No orders yet." if not all_orders else f"No {self._active_filter.lower()} orders."
            empty = QLabel(msg)
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                "color: #9ca3af; font-size: 15px; padding: 60px;"
                " background: transparent;"
            )
            self._orders_layout.insertWidget(0, empty)
            return

        for i, order in enumerate(orders):
            self._orders_layout.insertWidget(i, self._build_order_card(order))

    def _build_order_card(self, order):
        status = order.get("status", "Pending")
        fg, bg = ORDER_STATUS_STYLES.get(status, ("#6b7280", "#f9fafb"))

        card = QFrame()
        card.setStyleSheet("""
            QFrame { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; }
        """)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(12)

        # — Top row: order ID + status badge —
        top = QHBoxLayout()
        oid_lbl = QLabel(f"Order #{order['order_id']}")
        oid_lbl.setFont(QFont("Arial", 14, QFont.Bold))
        oid_lbl.setStyleSheet("color: #111827; background: transparent;")

        badge = QLabel(f"  {status}  ")
        badge.setFixedHeight(26)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            f"color: {fg}; background: {bg}; border: 1px solid {fg}55;"
            " border-radius: 6px; font-size: 12px; font-weight: 700;"
        )

        top.addWidget(oid_lbl)
        top.addStretch()
        top.addWidget(badge)
        layout.addLayout(top)

        # — Divider —
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #f3f4f6;")
        layout.addWidget(sep)

        # — Details —
        details = QHBoxLayout()
        details.setSpacing(24)

        left = QVBoxLayout()
        left.setSpacing(5)

        items_lbl = QLabel(f"🍽  {order.get('items', 'N/A')}")
        items_lbl.setStyleSheet(
            "color: #374151; font-size: 13px; background: transparent;"
        )
        items_lbl.setWordWrap(True)

        customer_lbl = QLabel(f"👤  {order.get('user_email', 'N/A')}")
        customer_lbl.setStyleSheet(
            "color: #6b7280; font-size: 12px; background: transparent;"
        )

        addr_lbl = QLabel(f"📍  {order.get('address', 'N/A')}")
        addr_lbl.setStyleSheet(
            "color: #6b7280; font-size: 12px; background: transparent;"
        )
        addr_lbl.setWordWrap(True)

        left.addWidget(items_lbl)
        left.addWidget(customer_lbl)
        left.addWidget(addr_lbl)

        right = QVBoxLayout()
        right.setSpacing(4)
        right.setAlignment(Qt.AlignTop | Qt.AlignRight)

        total_lbl = QLabel(f"EGP {order.get('total', '—')}")
        total_lbl.setFont(QFont("Arial", 16, QFont.Bold))
        total_lbl.setStyleSheet("color: #111827; background: transparent;")
        total_lbl.setAlignment(Qt.AlignRight)

        time_lbl = QLabel(f"🕐  {order.get('timestamp', 'N/A')}")
        time_lbl.setStyleSheet(
            "color: #9ca3af; font-size: 11px; background: transparent;"
        )
        time_lbl.setAlignment(Qt.AlignRight)

        pay_lbl = QLabel(f"💳  {order.get('payment_method', 'N/A')}")
        pay_lbl.setStyleSheet(
            "color: #6b7280; font-size: 12px; background: transparent;"
        )
        pay_lbl.setAlignment(Qt.AlignRight)

        right.addWidget(total_lbl)
        right.addWidget(time_lbl)
        right.addWidget(pay_lbl)

        details.addLayout(left, stretch=1)
        details.addLayout(right)
        layout.addLayout(details)

        # — Action buttons based on the current preparation stage —
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        if status == "Pending":
            reject_btn = QPushButton("✗  Reject Order")
            reject_btn.setFixedHeight(40)
            reject_btn.setMinimumWidth(140)
            reject_btn.setStyleSheet("""
                QPushButton { background: #fef2f2; color: #ef4444; border: 1px solid #fecaca;
                    border-radius: 8px; font-size: 13px; font-weight: 600; padding: 0 16px; }
                QPushButton:hover { background: #ef4444; color: white; border-color: #ef4444; }
            """)
            reject_btn.clicked.connect(
                lambda _ch, oid=order["order_id"]: self.handle_action(oid, "Rejected")
            )

            accept_btn = QPushButton("✓  Accept Order")
            accept_btn.setFixedHeight(40)
            accept_btn.setMinimumWidth(140)
            accept_btn.setStyleSheet("""
                QPushButton { background: #10b981; color: white; border: none;
                    border-radius: 8px; font-size: 13px; font-weight: 600; padding: 0 16px; }
                QPushButton:hover { background: #059669; }
            """)
            accept_btn.clicked.connect(
                lambda _ch, oid=order["order_id"]: self.handle_action(oid, "Accepted")
            )

            btn_row.addWidget(reject_btn)
            btn_row.addSpacing(8)
            btn_row.addWidget(accept_btn)
            layout.addLayout(btn_row)

        elif status == "Accepted":
            preparing_btn = QPushButton("👨‍🍳  Mark as Preparing")
            preparing_btn.setFixedHeight(40)
            preparing_btn.setMinimumWidth(180)
            preparing_btn.setStyleSheet("""
                QPushButton { background: #3b82f6; color: white; border: none;
                    border-radius: 8px; font-size: 13px; font-weight: 600; padding: 0 16px; }
                QPushButton:hover { background: #2563eb; }
            """)
            preparing_btn.clicked.connect(
                lambda _ch, oid=order["order_id"]: self.handle_action(oid, "Preparing")
            )
            btn_row.addWidget(preparing_btn)
            layout.addLayout(btn_row)

        elif status == "Preparing":
            ready_btn = QPushButton("📦  Mark as Ready for Pickup")
            ready_btn.setFixedHeight(40)
            ready_btn.setMinimumWidth(220)
            ready_btn.setStyleSheet("""
                QPushButton { background: #8b5cf6; color: white; border: none;
                    border-radius: 8px; font-size: 13px; font-weight: 600; padding: 0 16px; }
                QPushButton:hover { background: #7c3aed; }
            """)
            ready_btn.clicked.connect(
                lambda _ch, oid=order["order_id"]: self.handle_action(oid, "Ready for Pickup")
            )
            btn_row.addWidget(ready_btn)
            layout.addLayout(btn_row)

        return card

    def handle_action(self, order_id, status):
        order = get_order_by_id(order_id)
        if order is None:
            QMessageBox.warning(self, "Order Not Found", "This order could not be found.")
            self.refresh_orders()
            return

        if not self.restaurant_id or order.get("restaurant_id", "").strip() != self.restaurant_id:
            QMessageBox.warning(
                self,
                "Unauthorized Order",
                "This order does not belong to the restaurant linked to this account."
            )
            self.refresh_orders()
            return

        current_status = order.get("status", "Pending")
        allowed_next_statuses = VALID_STATUS_TRANSITIONS.get(current_status, set())

        if status not in allowed_next_statuses:
            QMessageBox.warning(
                self,
                "Invalid Status Update",
                f"Cannot change order from '{current_status}' to '{status}'."
            )
            self.refresh_orders()
            return

        if update_order_status_csv(order_id, status):
            QMessageBox.information(self, "Status Updated", f"Order is now '{status}'.")
        else:
            QMessageBox.warning(self, "Update Failed", "Could not update this order.")

        self.refresh_orders()


# ═════════════════════════════════════════════════════════════════════════════
# Admin Dashboard
# ═════════════════════════════════════════════════════════════════════════════
class AdminDashboard(QMainWindow):
    """Wasaly admin portal: complaints management (and future admin tools)."""

    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        name = user_data.get("full_name", "Admin")

        self.setWindowTitle("Wasaly — Admin Portal")
        self.resize(1100, 720)
        self.setStyleSheet("background: #f9fafb;")

        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("QFrame { background: #111827; }")
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(24, 32, 24, 32)
        sb.setSpacing(0)

        logo_lbl = QLabel("Wasaly")
        logo_lbl.setFont(QFont("Arial", 22, QFont.Bold))
        logo_lbl.setStyleSheet("color: #f0b100; background: transparent;")
        sb.addWidget(logo_lbl)

        portal_lbl = QLabel("Admin Portal")
        portal_lbl.setStyleSheet("color: #6b7280; font-size: 12px; background: transparent;")
        sb.addWidget(portal_lbl)
        sb.addSpacing(32)

        avatar_lbl = QLabel(name[0].upper() if name else "A")
        avatar_lbl.setFixedSize(56, 56)
        avatar_lbl.setAlignment(Qt.AlignCenter)
        avatar_lbl.setStyleSheet(
            "background: #6366f1; color: white; border-radius: 28px;"
            " font-size: 22px; font-weight: bold;"
        )
        sb.addWidget(avatar_lbl, alignment=Qt.AlignLeft)
        sb.addSpacing(12)

        name_lbl = QLabel(name)
        name_lbl.setFont(QFont("Arial", 14, QFont.Bold))
        name_lbl.setStyleSheet("color: #f9fafb; background: transparent;")
        name_lbl.setWordWrap(True)
        sb.addWidget(name_lbl)

        email_lbl = QLabel(user_data.get("email", ""))
        email_lbl.setStyleSheet("color: #9ca3af; font-size: 11px; background: transparent;")
        email_lbl.setWordWrap(True)
        sb.addWidget(email_lbl)
        sb.addSpacing(8)

        role_badge = QLabel("🛡  Wasaly Admin")
        role_badge.setStyleSheet("color: #6366f1; font-size: 11px; font-weight: 700; background: transparent;")
        sb.addWidget(role_badge)
        sb.addSpacing(24)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: #374151;")
        sb.addWidget(div)
        sb.addSpacing(20)

        # Sidebar nav buttons
        def _nav_btn(icon, label, on_click):
            btn = QPushButton(f"{icon}  {label}")
            btn.setFixedHeight(42)
            btn.setStyleSheet("""
                QPushButton { background: #1f2937; color: #d1d5db; border: none;
                    border-radius: 8px; text-align: left; padding: 0 14px;
                    font-size: 13px; font-weight: 600; }
                QPushButton:hover { background: #374151; color: white; }
            """)
            btn.clicked.connect(on_click)
            return btn

        sb.addWidget(_nav_btn("🎫", "Complaints", lambda: self.stack.setCurrentIndex(1)))
        sb.addSpacing(6)
        sb.addWidget(_nav_btn("🏠", "Dashboard",  lambda: self.stack.setCurrentIndex(0)))
        sb.addStretch()

        logout_btn = QPushButton("Sign Out")
        logout_btn.setFixedHeight(40)
        logout_btn.setStyleSheet("""
            QPushButton { background: #1f2937; color: #9ca3af; border: 1px solid #374151;
                border-radius: 8px; font-size: 13px; font-weight: 600; }
            QPushButton:hover { background: #374151; color: white; }
        """)
        logout_btn.clicked.connect(self._logout)
        sb.addWidget(logout_btn)

        root.addWidget(sidebar)

        # ── Stacked main area ─────────────────────────────────────────────────
        self.stack = QStackedWidget()

        # Index 0: Admin home
        home_page = self._build_home_page(name)
        self.stack.addWidget(home_page)   # 0

        # Index 1: Complaints
        self.complaints_widget = AdminComplaintsWidget(user_data)
        self.complaints_widget.go_back.connect(lambda: self.stack.setCurrentIndex(0))
        self.stack.addWidget(self.complaints_widget)  # 1

        root.addWidget(self.stack, stretch=1)

    def _build_home_page(self, name):
        page = QWidget()
        page.setStyleSheet("background: #f9fafb;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(40, 40, 40, 40)
        lay.setSpacing(20)

        welcome = QLabel(f"Welcome, {name.split()[0]}! 🛡")
        welcome.setFont(QFont("Arial", 24, QFont.Bold))
        welcome.setStyleSheet("color: #111827;")

        subtitle = QLabel("Wasaly Admin Portal — manage complaints and platform health.")
        subtitle.setStyleSheet("color: #6b7280; font-size: 14px;")

        lay.addWidget(welcome)
        lay.addWidget(subtitle)
        lay.addSpacing(16)

        # Quick-action card for complaints
        card = QFrame()
        card.setFixedHeight(160)
        card.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 16px; }"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 20)
        cl.setSpacing(8)

        icon_lbl = QLabel("🎫")
        icon_lbl.setFont(QFont("Arial", 20))
        icon_lbl.setStyleSheet("background: transparent;")

        title_lbl = QLabel("Complaints & Escalations")
        title_lbl.setFont(QFont("Arial", 14, QFont.Bold))
        title_lbl.setStyleSheet("color: #111827; background: transparent;")

        desc_lbl = QLabel("View, respond to, and resolve customer complaints.")
        desc_lbl.setStyleSheet("color: #6b7280; font-size: 13px; background: transparent;")

        open_btn = QPushButton("Open →")
        open_btn.setFixedHeight(34)
        open_btn.setFixedWidth(100)
        open_btn.setStyleSheet("""
            QPushButton { background: #6366f1; color: white; border: none;
                border-radius: 8px; font-size: 13px; font-weight: 700; }
            QPushButton:hover { background: #4f46e5; }
        """)
        open_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        cl.addWidget(icon_lbl)
        cl.addWidget(title_lbl)
        cl.addWidget(desc_lbl)
        cl.addStretch()
        cl.addWidget(open_btn, alignment=Qt.AlignLeft)

        lay.addWidget(card)
        lay.addStretch()
        return page

    def _logout(self):
        clear_session()
        self.auth_window = AuthWindow()
        center_window(self.auth_window)
        self.auth_window.show()
        self.close()


class AuthWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_login = True
        self.role_window = None
        self.setWindowTitle("Wasaly")
        self.resize(1100, 700)

        self.setStyleSheet("""
            QMainWindow {
                background: #ffffff;
            }

            QFrame#LeftPanel {
                background-color: #1f1f1f;
                border: none;
            }

            QFrame#RightPanel {
                background-color: white;
                border: none;
            }

            QLabel#FormSubtitle {
                color: #6b7280;
                font-size: 14px;
            }

            QLabel#FieldLabel {
                color: #374151;
                font-size: 13px;
                font-weight: 600;
            }

            QLineEdit {
                border: 1px solid #d1d5db;
                border-radius: 10px;
                padding: 12px 14px;
                font-size: 14px;
                background: white;
            }

            QLineEdit:focus {
                border: 2px solid #f0b100;
            }

            QPushButton#ToggleButton {
                background: transparent;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                font-weight: 600;
                color: #6b7280;
            }

            QPushButton#ToggleActive {
                background: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                font-weight: 600;
                color: #111827;
            }

            QFrame#ToggleContainer {
                background: #f3f4f6;
                border-radius: 10px;
            }

            QPushButton#PrimaryButton {
                background-color: #f0b100;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px;
                font-size: 15px;
                font-weight: 600;
            }

            QPushButton#PrimaryButton:hover {
                background-color: #d99f00;
            }

            QPushButton#LinkButton {
                background: transparent;
                border: none;
                color: #d99f00;
                font-size: 13px;
                font-weight: 600;
                text-align: right;
            }

            QPushButton#SocialButton {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
                padding: 12px;
                font-size: 14px;
                font-weight: 600;
                color: #374151;
            }

            QPushButton#SocialButton:hover {
                background: #f9fafb;
            }

            QCheckBox {
                color: #4b5563;
                font-size: 13px;
            }

            QFrame#Divider {
                background: #d1d5db;
                min-height: 1px;
                max-height: 1px;
            }
        """)

        self.build_ui()
        self.update_mode()

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        left_panel = QFrame()
        left_panel.setObjectName("LeftPanel")
        left_panel.setMinimumWidth(420)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        side_image_label = QLabel()
        side_image_label.setAlignment(Qt.AlignCenter)
        side_pixmap = QPixmap(SIDE_IMAGE_PATH)

        if not side_pixmap.isNull():
            scaled = side_pixmap.scaled(
                600, 900,
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            side_image_label.setPixmap(scaled)
            side_image_label.setScaledContents(True)
        else:
            side_image_label.setText("sidescreen.png not found")
            side_image_label.setStyleSheet("color: white; font-size: 20px;")
            side_image_label.setAlignment(Qt.AlignCenter)

        left_layout.addWidget(side_image_label)

        right_panel = QFrame()
        right_panel.setObjectName("RightPanel")

        right_outer = QVBoxLayout(right_panel)
        right_outer.setContentsMargins(80, 40, 80, 40)
        right_outer.addStretch()

        form_container = QWidget()
        form_container.setMaximumWidth(430)

        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(16)

        self.subtitle = QLabel("Welcome back! Please enter your details.")
        self.subtitle.setObjectName("FormSubtitle")
        form_layout.addWidget(self.subtitle)
        form_layout.addSpacing(10)

        toggle_container = QFrame()
        toggle_container.setObjectName("ToggleContainer")

        toggle_layout = QHBoxLayout(toggle_container)
        toggle_layout.setContentsMargins(4, 4, 4, 4)
        toggle_layout.setSpacing(6)

        self.login_toggle = QPushButton("Login")
        self.login_toggle.clicked.connect(self.set_login_mode)

        self.register_toggle = QPushButton("Register")
        self.register_toggle.clicked.connect(self.set_register_mode)

        toggle_layout.addWidget(self.login_toggle)
        toggle_layout.addWidget(self.register_toggle)
        form_layout.addWidget(toggle_container)

        self.name_label = QLabel("Full Name")
        self.name_label.setObjectName("FieldLabel")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("John Doe")

        self.email_label = QLabel("Email")
        self.email_label.setObjectName("FieldLabel")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("you@example.com")

        self.phone_label = QLabel("Phone Number")
        self.phone_label.setObjectName("FieldLabel")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+20XXXXXXXXXX")

        self.password_label = QLabel("Password")
        self.password_label.setObjectName("FieldLabel")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.confirm_label = QLabel("Confirm Password")
        self.confirm_label.setObjectName("FieldLabel")
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("••••••••")
        self.confirm_input.setEchoMode(QLineEdit.Password)

        self.role_label = QLabel("Account Type")
        self.role_label.setObjectName("FieldLabel")
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Customer", "Restaurant Owner"])
        self.role_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #d1d5db; border-radius: 10px;
                padding: 12px 14px; font-size: 14px; background: white; color: #111827;
            }
            QComboBox:focus { border: 2px solid #f0b100; }
            QComboBox QAbstractItemView {
                background: white; color: #111827; border: 1px solid #d1d5db;
                selection-background-color: #f0b100; selection-color: white;
            }
        """)

        form_layout.addWidget(self.name_label)
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(self.email_label)
        form_layout.addWidget(self.email_input)
        form_layout.addWidget(self.phone_label)
        form_layout.addWidget(self.phone_input)
        form_layout.addWidget(self.password_label)
        form_layout.addWidget(self.password_input)
        form_layout.addWidget(self.confirm_label)
        form_layout.addWidget(self.confirm_input)
        form_layout.addWidget(self.role_label)
        form_layout.addWidget(self.role_combo)

        login_row = QHBoxLayout()
        self.remember_check = QCheckBox("Remember me")

        self.forgot_button = QPushButton("Forgot password?")
        self.forgot_button.setObjectName("LinkButton")
        self.forgot_button.clicked.connect(self.show_forgot_password_info)

        login_row.addWidget(self.remember_check)
        login_row.addStretch()
        login_row.addWidget(self.forgot_button)
        form_layout.addLayout(login_row)

        self.submit_button = QPushButton("Sign In")
        self.submit_button.setObjectName("PrimaryButton")
        self.submit_button.clicked.connect(self.handle_submit)
        form_layout.addWidget(self.submit_button)

        right_outer.addWidget(form_container, alignment=Qt.AlignCenter)
        right_outer.addStretch()

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 1)

    def set_login_mode(self):
        self.is_login = True
        self.update_mode()

    def set_register_mode(self):
        self.is_login = False
        self.update_mode()

    def update_mode(self):
        _active = """
            QPushButton#ToggleActive {
                background: white; border: none; border-radius: 8px; padding: 10px;
                font-size: 14px; font-weight: 600; color: #111827;
            }
        """
        _inactive = """
            QPushButton {
                background: transparent; border: none; border-radius: 8px; padding: 10px;
                font-size: 14px; font-weight: 600; color: #6b7280;
            }
            QPushButton:hover { color: #374151; }
        """
        if self.is_login:
            self.login_toggle.setStyleSheet(_active)
            self.register_toggle.setStyleSheet(_inactive)
            self.submit_button.setText("Sign In")
            self.subtitle.setText("Welcome back! Please enter your details.")

            self.name_label.hide(); self.name_input.hide()
            self.phone_label.hide(); self.phone_input.hide()
            self.confirm_label.hide(); self.confirm_input.hide()
            self.role_label.hide(); self.role_combo.hide()
            self.remember_check.show()
            self.forgot_button.show()
        else:
            self.login_toggle.setStyleSheet(_inactive)
            self.register_toggle.setStyleSheet(_active)
            self.submit_button.setText("Create Account")
            self.subtitle.setText("Create your account and get started.")

            self.name_label.show(); self.name_input.show()
            self.phone_label.show(); self.phone_input.show()
            self.confirm_label.show(); self.confirm_input.show()
            self.role_label.show(); self.role_combo.show()
            self.remember_check.hide()
            self.forgot_button.hide()

    def build_role_window(self, user_data):
        role = user_data.get("role", "User")
        if role == "Restaurant":
            return RestaurantDashboard(user_data)
        elif role == "Admin":
            return AdminDashboard(user_data)
        else:
            return RoleWindow(user_data)

    def show_role_window(self, user_data):
        self.role_window = self.build_role_window(user_data)
        center_window(self.role_window)
        self.role_window.show()
        self.close()

    def show_forgot_password_info(self):
        QMessageBox.information(
            self, "Reset Password",
            "Password reset via email is coming soon.\n\n"
            "If you need urgent access, please contact support."
        )

    def handle_login(self, email, password):
        user = find_user_by_email(email)

        if user is None:
            QMessageBox.information(
                self, "Not Registered",
                "This email is not registered. Please create an account first."
            )
            self.set_register_mode()
            return

        if user["password"] != password:
            QMessageBox.warning(self, "Login Failed", "Incorrect email or password.")
            return

        if self.remember_check.isChecked():
            save_session(user)

        self.show_role_window(user)

    def handle_register(self, name, email, phone, password, confirm, role_text):
        if len(password) < 8:
            QMessageBox.warning(self, "Error", "Password must be at least 8 characters.")
            return

        if password != confirm:
            QMessageBox.warning(self, "Error", "Passwords do not match.")
            return

        if not email.endswith(".com"):
            QMessageBox.warning(self, "Error", "Please enter a valid email address.")
            return

        if not phone.startswith("+20"):
            QMessageBox.warning(self, "Error", "Phone number must start with +20.")
            return

        number_part = phone[3:]
        if not number_part.isdigit() or len(number_part) != 10:
            QMessageBox.warning(
                self, "Error", "Phone must be +20 followed by exactly 10 digits."
            )
            return

        if find_user_by_email(email) is not None:
            QMessageBox.warning(
                self, "Already Registered",
                "An account with this email already exists. Please sign in."
            )
            self.set_login_mode()
            return

        role = "Restaurant" if role_text == "Restaurant Owner" else "User"
        new_user = {
            "full_name": name,
            "email": email,
            "phone": phone,
            "password": password,
            "role": role,
        }

        append_user(new_user)
        self.show_role_window(new_user)

    def handle_submit(self):
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()

        if self.is_login:
            if not email or not password:
                QMessageBox.warning(self, "Error", "Please enter your email and password.")
                return
            self.handle_login(email, password)
        else:
            name    = self.name_input.text().strip()
            phone   = self.phone_input.text().strip()
            confirm = self.confirm_input.text().strip()
            role    = self.role_combo.currentText()

            if not name or not email or not phone or not password or not confirm:
                QMessageBox.warning(self, "Error", "Please fill in all fields.")
                return

            self.handle_register(name, email, phone, password, confirm, role)


def center_window(window):
    screen = QApplication.primaryScreen().availableGeometry()
    frame = window.frameGeometry()
    frame.moveCenter(screen.center())
    window.move(frame.topLeft())


def main():
    app = QApplication(sys.argv)

    if not os.path.exists(SPLASH_PATH):
        print("Error: splashscreen.png was not found.")
        sys.exit(1)

    if not os.path.exists(SIDE_IMAGE_PATH):
        print("Error: sidescreen.png was not found.")
        sys.exit(1)

    ensure_csv_exists()

    splash = SplashScreen()
    auth_window = AuthWindow()

    center_window(splash)
    splash.show()

    def show_auth():
        splash.close()
        saved_user = load_session()
        if saved_user:
            # Auto-login: skip the auth window entirely
            role_win = auth_window.build_role_window(saved_user)
            center_window(role_win)
            role_win.show()
        else:
            auth_window.show()
            center_window(auth_window)

    QTimer.singleShot(2000, show_auth)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()