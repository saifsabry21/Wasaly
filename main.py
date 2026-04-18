import csv
import json
import os
import sys
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QLabel, QPushButton,
    QLineEdit, QHBoxLayout, QVBoxLayout, QFrame, QMessageBox,
    QCheckBox, QStackedWidget
)
from nearby_restaurants import NearbyRestaurantsWidget
from restaurant_details import RestaurantDetailsWidget
from cart_order import CartOrderWidget

SPLASH_PATH = "splashscreen.png"
SIDE_IMAGE_PATH = "sidescreen.png"
CSV_PATH = "users_data.csv"
CSV_HEADERS = ["full_name", "email", "phone", "password", "role"]
ORDERS_CSV = "orders_data.csv"
ORDERS_HEADERS = ["order_id", "restaurant_id", "items", "status"]
SESSION_PATH = "session.json"

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
    if os.path.exists(CSV_PATH):
        return

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(DUMMY_USERS)


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
    orders = []
    if not os.path.exists(ORDERS_CSV):
        return orders
    with open(ORDERS_CSV, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            orders.append(row)
    return orders


def update_order_status_csv(order_id, new_status):
    orders = load_orders()
    for order in orders:
        if order["order_id"] == str(order_id):
            order["status"] = new_status

    with open(ORDERS_CSV, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=ORDERS_HEADERS)
        writer.writeheader()
        writer.writerows(orders)



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

        cart_card   = _placeholder_card("🛒", "My Cart & Checkout", "Sprint 2")
        orders_card = _placeholder_card("📦", "Track My Orders",    "Sprint 2")
        reviews_card = _placeholder_card("⭐", "Ratings & Reviews", "Sprint 3")

        cards_layout.addWidget(nearby_card)
        cards_layout.addWidget(cart_card)
        cards_layout.addWidget(orders_card)
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

class RestaurantDashboard(QMainWindow):
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        role = user_data.get("role", "Restaurant")
        name = user_data.get("full_name", "Restaurant Owner")

        self.setWindowTitle(f"Wasaly - {role} Dashboard")
        self.resize(900, 600)
        self.setStyleSheet("background: #ffffff;")

        central = QWidget()
        self.setCentralWidget(central)

        self.layout = QVBoxLayout(central)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(18)

        # Header matching Jana's style
        title = QLabel("Restaurant Dashboard")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setStyleSheet("color: #111827;")

        welcome = QLabel(f"Welcome back, {name}")
        welcome.setFont(QFont("Arial", 16))
        welcome.setStyleSheet("color: #374151;")

        self.layout.addWidget(title)
        self.layout.addWidget(welcome)

        # Area to hold the orders
        self.orders_container = QVBoxLayout()
        self.orders_container.setSpacing(15)
        self.layout.addLayout(self.orders_container)
        self.layout.addStretch()

        self.refresh_orders()

    def refresh_orders(self):
        # Clear old order cards before redrawing
        for i in reversed(range(self.orders_container.count())):
            widget = self.orders_container.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        orders = load_orders()

        if not orders:
            empty = QLabel("No orders available.")
            empty.setStyleSheet("color: #6b7280; font-size: 14px;")
            self.orders_container.addWidget(empty)
            return

        for order in orders:
            # Create a card for each order using Jana's styling
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background: #f9fafb; 
                    border: 1px solid #e5e7eb; 
                    border-radius: 10px; 
                }
            """)
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(20, 20, 20, 20)

            # Order Info
            info = QLabel(
                f"<b>Order #{order['order_id']}</b><br><br>Items: {order['items']}<br>Status: <b>{order['status']}</b>")
            info.setStyleSheet("color: #374151; font-size: 14px; border: none; background: transparent;")
            card_layout.addWidget(info)
            card_layout.addStretch()

            # Add Accept/Reject buttons only if Pending
            if order['status'] == "Pending":
                accept_btn = QPushButton("Accept")
                accept_btn.setFixedSize(100, 40)
                accept_btn.setStyleSheet("""
                    QPushButton { background-color: #10b981; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; }
                    QPushButton:hover { background-color: #059669; }
                """)
                accept_btn.clicked.connect(lambda ch, o=order['order_id']: self.handle_action(o, "Accepted"))

                reject_btn = QPushButton("Reject")
                reject_btn.setFixedSize(100, 40)
                reject_btn.setStyleSheet("""
                    QPushButton { background-color: #ef4444; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; }
                    QPushButton:hover { background-color: #dc2626; }
                """)
                reject_btn.clicked.connect(lambda ch, o=order['order_id']: self.handle_action(o, "Rejected"))

                card_layout.addWidget(accept_btn)
                card_layout.addSpacing(10)
                card_layout.addWidget(reject_btn)

            self.orders_container.addWidget(card)

    def handle_action(self, order_id, status):
        update_order_status_csv(order_id, status)
        QMessageBox.information(self, "Order Updated", f"Order #{order_id} has been {status}.")
        self.refresh_orders()  # Instantly update the UI


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

        form_layout.addWidget(self.name_label)
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(self.email_label)
        form_layout.addWidget(self.email_input)
        form_layout.addWidget(self.phone_label)
        form_layout.addWidget(self.phone_input)
        form_layout.addWidget(self.password_label)
        form_layout.addWidget(self.password_input)

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

        self.social_section = QWidget()
        social_layout = QVBoxLayout(self.social_section)
        social_layout.setContentsMargins(0, 10, 0, 0)
        social_layout.setSpacing(14)

        divider_row = QHBoxLayout()
        left_div = QFrame()
        left_div.setObjectName("Divider")
        right_div = QFrame()
        right_div.setObjectName("Divider")

        or_label = QLabel("Or continue with")
        or_label.setStyleSheet("color: #6b7280; font-size: 13px;")

        divider_row.addWidget(left_div)
        divider_row.addWidget(or_label)
        divider_row.addWidget(right_div)

        social_buttons = QHBoxLayout()
        google_btn = QPushButton("Google")
        google_btn.setObjectName("SocialButton")
        github_btn = QPushButton("Facebook")
        github_btn.setObjectName("SocialButton")

        social_buttons.addWidget(google_btn)
        social_buttons.addWidget(github_btn)

        social_layout.addLayout(divider_row)
        social_layout.addLayout(social_buttons)
        form_layout.addWidget(self.social_section)

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
        if self.is_login:
            self.login_toggle.setObjectName("ToggleActive")
            self.register_toggle.setObjectName("ToggleButton")
            self.submit_button.setText("Sign In")
            self.subtitle.setText("Welcome back! Please enter your details.")

            self.name_label.hide()
            self.name_input.hide()
            self.phone_label.hide()
            self.phone_input.hide()

            self.remember_check.show()
            self.forgot_button.show()
            self.social_section.show()
        else:
            self.login_toggle.setObjectName("ToggleButton")
            self.register_toggle.setObjectName("ToggleActive")
            self.submit_button.setText("Create Account")
            self.subtitle.setText("Create your account and get started.")

            self.name_label.show()
            self.name_input.show()
            self.phone_label.show()
            self.phone_input.show()

            self.remember_check.hide()
            self.forgot_button.hide()
            self.social_section.hide()

        self.style().unpolish(self.login_toggle)
        self.style().polish(self.login_toggle)
        self.style().unpolish(self.register_toggle)
        self.style().polish(self.register_toggle)

    def build_role_window(self, user_data):
        role = user_data.get("role", "User")
        if role == "Restaurant":
            return RestaurantDashboard(user_data)
        else:
            return RoleWindow(user_data)

    def show_role_window(self, user_data):
        self.role_window = self.build_role_window(user_data)
        center_window(self.role_window)
        self.role_window.show()
        self.close()

    def show_forgot_password_info(self):
        email = self.email_input.text().strip()
        if not email:
            QMessageBox.information(
                self,
                "Forgot Password",
                "Enter your email first, then check users_data.csv to update the password manually for now."
            )
            return

        user = find_user_by_email(email)
        if user is None:
            QMessageBox.information(
                self,
                "Forgot Password",
                "This email is not registered yet. Please create an account first."
            )
        else:
            QMessageBox.information(
                self,
                "Forgot Password",
                f"Account found for {email}. For now, update the password manually inside users_data.csv."
            )

    def handle_login(self, email, password):
        user = find_user_by_email(email)

        if user is None:
            QMessageBox.information(
                self,
                "Not Registered",
                "This email is not registered. Please register first."
            )
            self.set_register_mode()
            return

        if user["password"] != password:
            QMessageBox.warning(self, "Login Failed", "Incorrect password.")
            return

        if self.remember_check.isChecked():
            save_session(user)

        QMessageBox.information(
            self,
            "Login Successful",
            f"Welcome back, {user['full_name']}!"
        )
        self.show_role_window(user)

    def handle_register(self, name, email, phone, password):
        if not email.endswith(".com"):
            QMessageBox.warning(self, "Error", "Email must end with .com")
            return

        if not phone.startswith("+20"):
            QMessageBox.warning(self, "Error", "Phone number must start with +20")
            return

        number_part = phone[3:]
        if not number_part.isdigit() or len(number_part) != 10:
            QMessageBox.warning(
                self,
                "Error",
                "Phone must be +20 followed by exactly 10 digits"
            )
            return

        existing_user = find_user_by_email(email)
        if existing_user is not None:
            QMessageBox.warning(
                self,
                "Already Registered",
                "This email already exists. Please log in instead."
            )
            self.set_login_mode()
            return

        users = load_users()
        for user in users:
            if user["password"] == password:
                QMessageBox.warning(
                    self,
                    "Error",
                    "This password is already used. Choose another one."
                )
                return

        new_user = {
            "full_name": name,
            "email": email,
            "phone": phone,
            "password": password,
            "role": "User",
        }

        append_user(new_user)
        QMessageBox.information(
            self,
            "Registration Successful",
            "Account created successfully. You can now use your new account."
        )
        self.show_role_window(new_user)

    def handle_submit(self):
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()

        if self.is_login:
            if not email or not password:
                QMessageBox.warning(self, "Error", "Please fill in email and password.")
                return
            self.handle_login(email, password)
        else:
            name = self.name_input.text().strip()
            phone = self.phone_input.text().strip()

            if not name or not email or not phone or not password:
                QMessageBox.warning(
                    self,
                    "Error",
                    "Please fill in all registration fields."
                )
                return

            self.handle_register(name, email, phone, password)


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