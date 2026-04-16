"""
Wasaly - Discover Nearby Restaurants Feature
User Story: As a customer, I want to see nearby restaurants based on my location
            so that I can easily find options around me.

Live restaurant data is fetched from OpenStreetMap via the Overpass API —
no API key required. Falls back to curated Cairo data if offline.
"""

import math
import urllib.request, urllib.parse, json
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QFrame, QScrollArea,
    QComboBox, QMessageBox, QProgressBar, QSizePolicy
)

# ── Fallback restaurant data (used when offline) ──────────────────────────────
FALLBACK_RESTAURANTS = [
    {"id": "R01", "name": "Koshary El Tahrir",       "address": "Tahrir Square, Downtown",        "lat": 30.0444, "lon": 31.2357, "category": "Egyptian", "rating": 4.5, "delivery_time": 15, "fee": 5.0},
    {"id": "R02", "name": "Kebdet El Prince",         "address": "Mohammed Ali St, Downtown",      "lat": 30.0480, "lon": 31.2480, "category": "Egyptian", "rating": 4.4, "delivery_time": 20, "fee": 7.0},
    {"id": "R03", "name": "Felfela Restaurant",       "address": "Hoda Shaarawy St, Downtown",     "lat": 30.0461, "lon": 31.2390, "category": "Egyptian", "rating": 4.3, "delivery_time": 25, "fee": 10.0},
    {"id": "R04", "name": "Maison Thomas",            "address": "26 July St, Zamalek",            "lat": 30.0594, "lon": 31.2194, "category": "Italian",  "rating": 4.6, "delivery_time": 30, "fee": 20.0},
    {"id": "R05", "name": "Cairo Kitchen",            "address": "Zamalek",                        "lat": 30.0620, "lon": 31.2210, "category": "Egyptian", "rating": 4.5, "delivery_time": 25, "fee": 15.0},
    {"id": "R06", "name": "Ovio Cafe & Bistro",       "address": "Zamalek",                        "lat": 30.0610, "lon": 31.2230, "category": "Cafe",     "rating": 4.4, "delivery_time": 20, "fee": 18.0},
    {"id": "R07", "name": "Peking Restaurant",        "address": "Orabi St, Heliopolis",           "lat": 30.0872, "lon": 31.3221, "category": "Chinese",  "rating": 4.3, "delivery_time": 30, "fee": 15.0},
    {"id": "R08", "name": "Tikka Grill",              "address": "Al-Ahram St, Heliopolis",        "lat": 30.0890, "lon": 31.3260, "category": "Grills",   "rating": 4.6, "delivery_time": 25, "fee": 18.0},
    {"id": "R09", "name": "Cilantro Coffee",          "address": "Baghdad St, Heliopolis",         "lat": 30.0855, "lon": 31.3300, "category": "Cafe",     "rating": 4.2, "delivery_time": 15, "fee": 10.0},
    {"id": "R10", "name": "Lucille's",                "address": "Road 9, Maadi",                  "lat": 29.9620, "lon": 31.2580, "category": "American", "rating": 4.5, "delivery_time": 30, "fee": 20.0},
    {"id": "R11", "name": "Maadi House",              "address": "Road 257, Maadi",                "lat": 29.9600, "lon": 31.2560, "category": "Egyptian", "rating": 4.3, "delivery_time": 20, "fee": 8.0},
    {"id": "R12", "name": "Mughal Mahal",             "address": "Road 9, Maadi",                  "lat": 29.9640, "lon": 31.2590, "category": "Indian",   "rating": 4.4, "delivery_time": 35, "fee": 22.0},
    {"id": "R13", "name": "Hardee's Nasr City",       "address": "Abbas El Akkad, Nasr City",      "lat": 30.0650, "lon": 31.3460, "category": "Burgers",  "rating": 4.1, "delivery_time": 20, "fee": 12.0},
    {"id": "R14", "name": "Shawarmer",                "address": "Makram Ebeid, Nasr City",        "lat": 30.0670, "lon": 31.3500, "category": "Lebanese", "rating": 4.3, "delivery_time": 18, "fee": 8.0},
    {"id": "R15", "name": "Pizza Hut Nasr City",      "address": "Nasr City",                      "lat": 30.0680, "lon": 31.3420, "category": "Italian",  "rating": 4.0, "delivery_time": 35, "fee": 15.0},
    {"id": "R16", "name": "The Grill Room",           "address": "90th St, New Cairo",             "lat": 30.0050, "lon": 31.4600, "category": "Grills",   "rating": 4.7, "delivery_time": 25, "fee": 20.0},
    {"id": "R17", "name": "Burger King New Cairo",    "address": "Cairo Festival City, New Cairo", "lat": 30.0290, "lon": 31.4820, "category": "Burgers",  "rating": 4.1, "delivery_time": 20, "fee": 10.0},
    {"id": "R18", "name": "Sushi Samba",              "address": "Point 90 Mall, New Cairo",       "lat": 30.0070, "lon": 31.4650, "category": "Japanese", "rating": 4.6, "delivery_time": 40, "fee": 30.0},
    {"id": "R19", "name": "Koshary El Tahrir NC",     "address": "New Cairo Branch",               "lat": 30.0120, "lon": 31.4700, "category": "Egyptian", "rating": 4.4, "delivery_time": 15, "fee": 6.0},
    {"id": "R20", "name": "Jones The Grocer",         "address": "Waterway, New Cairo",            "lat": 30.0200, "lon": 31.4750, "category": "Cafe",     "rating": 4.5, "delivery_time": 30, "fee": 25.0},
    {"id": "R21", "name": "Koshary (Madinaty Mall)",  "address": "Madinaty Mall",                  "lat": 30.1180, "lon": 31.6050, "category": "Egyptian", "rating": 4.2, "delivery_time": 15, "fee": 5.0},
    {"id": "R22", "name": "McDonald's Madinaty",      "address": "Madinaty",                       "lat": 30.1160, "lon": 31.6030, "category": "Burgers",  "rating": 4.0, "delivery_time": 20, "fee": 10.0},
    {"id": "R23", "name": "Sugaryaki",                "address": "Madinaty",                       "lat": 30.1200, "lon": 31.6080, "category": "Japanese", "rating": 4.5, "delivery_time": 35, "fee": 22.0},
    {"id": "R24", "name": "Shorouk Kitchen",          "address": "El Shorouk City",                "lat": 30.1450, "lon": 31.6100, "category": "Egyptian", "rating": 4.1, "delivery_time": 20, "fee": 7.0},
    {"id": "R25", "name": "Pizza Corner Shorouk",     "address": "El Shorouk",                     "lat": 30.1430, "lon": 31.6080, "category": "Italian",  "rating": 4.0, "delivery_time": 30, "fee": 15.0},
    {"id": "R26", "name": "Abou El Sid",              "address": "26 July St, Mohandessin",        "lat": 30.0560, "lon": 31.2050, "category": "Egyptian", "rating": 4.7, "delivery_time": 30, "fee": 18.0},
    {"id": "R27", "name": "Sequoia",                  "address": "Abu El Feda, Zamalek",           "lat": 30.0650, "lon": 31.2170, "category": "Grills",   "rating": 4.6, "delivery_time": 35, "fee": 25.0},
    {"id": "R28", "name": "Kimo's Fish",              "address": "Sphinx Square, Mohandessin",     "lat": 30.0580, "lon": 31.2070, "category": "Seafood",  "rating": 4.4, "delivery_time": 25, "fee": 20.0},
]

LOCATION_PRESETS = {
    "Tahrir Square":              (30.0444, 31.2357),
    "Zamalek":                    (30.0600, 31.2198),
    "Heliopolis":                 (30.0875, 31.3388),
    "Maadi":                      (29.9603, 31.2569),
    "Nasr City":                  (30.0673, 31.3469),
    "Dokki":                      (30.0382, 31.2118),
    "Mohandessin":                (30.0572, 31.2014),
    "New Cairo (5th Settlement)": (30.0091, 31.4681),
    "Madinaty":                   (30.1170, 31.6040),
    "El Shorouk":                 (30.1440, 31.6090),
    "El Rehab":                   (30.0720, 31.5000),
    "Obour City":                 (30.2100, 31.4900),
}

CATEGORY_COLORS = {
    "Egyptian": "#f59e0b", "Italian":  "#10b981", "Burgers":  "#3b82f6",
    "Japanese": "#8b5cf6", "Lebanese": "#ec4899", "Grills":   "#ef4444",
    "American": "#6366f1", "Indian":   "#f97316", "Chinese":  "#14b8a6",
    "Seafood":  "#0ea5e9", "Cafe":     "#a78bfa", "Healthy":  "#22c55e",
    "Restaurant": "#6b7280", "Fast Food": "#f97316", "Pizza": "#10b981",
}

# cuisine tag from OSM → our category labels
CUISINE_MAP = {
    "egyptian": "Egyptian", "koshary": "Egyptian", "foul": "Egyptian",
    "italian": "Italian", "pizza": "Italian",
    "burger": "Burgers", "american": "American", "fast_food": "Burgers",
    "japanese": "Japanese", "sushi": "Japanese",
    "lebanese": "Lebanese", "shawarma": "Lebanese", "arabic": "Lebanese",
    "indian": "Indian",  "chinese": "Chinese",
    "seafood": "Seafood", "fish": "Seafood",
    "coffee": "Cafe", "cafe": "Cafe",
    "grill": "Grills", "barbecue": "Grills", "kebab": "Grills",
}


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def fetch_osm_restaurants(lat, lon, radius_km):
    """
    Fetch real restaurants from OpenStreetMap Overpass API.
    Returns a list of restaurant dicts, or None if the request fails.
    """
    radius_m = int(radius_km * 1000)
    query = (
        f'[out:json][timeout:15];'
        f'('
        f'  node["amenity"="restaurant"](around:{radius_m},{lat},{lon});'
        f'  node["amenity"="fast_food"](around:{radius_m},{lat},{lon});'
        f'  node["amenity"="cafe"](around:{radius_m},{lat},{lon});'
        f');'
        f'out body 40;'
    )
    try:
        data = urllib.parse.urlencode({"data": query}).encode()
        req = urllib.request.Request(
            "https://overpass-api.de/api/interpreter",
            data=data,
            headers={"User-Agent": "WasalyApp/1.0 (student project)"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read().decode())

        restaurants = []
        for i, el in enumerate(result.get("elements", [])):
            tags = el.get("tags", {})
            # Prefer English name; fall back to Arabic name only if no Latin name exists
            name_en = tags.get("name:en", "").strip()
            name_ar = tags.get("name:ar", "").strip()
            name_default = tags.get("name", "").strip()

            # Check if default name is Latin script (not Arabic)
            def is_latin(s):
                return all(ord(c) < 1536 for c in s if c.isalpha())

            if name_en:
                name = name_en
            elif is_latin(name_default) and name_default:
                name = name_default
            elif name_ar:
                name = name_ar   # Arabic fallback — will be shown as-is
            elif name_default:
                name = name_default
            else:
                continue  # skip unnamed places

            cuisine_raw = tags.get("cuisine", "").lower().split(";")[0].strip()
            category = CUISINE_MAP.get(cuisine_raw, "Restaurant")
            if tags.get("amenity") == "cafe":
                category = "Cafe"
            elif tags.get("amenity") == "fast_food" and category == "Restaurant":
                category = "Burgers"

            ARABIC_CITY_MAP = {
                "القاهرة": "Cairo", "الجيزة": "Giza", "الإسكندرية": "Alexandria",
                "مدينة نصر": "Nasr City", "المعادي": "Maadi", "الزمالك": "Zamalek",
                "مصر الجديدة": "Heliopolis", "التجمع الخامس": "New Cairo",
                "المهندسين": "Mohandessin", "الدقي": "Dokki", "مدينتي": "Madinaty",
                "الشروق": "El Shorouk",
            }
            def clean_addr(s):
                return ARABIC_CITY_MAP.get(s.strip(), s.strip()) if s else ""

            street_raw = tags.get("addr:street", "") or tags.get("addr:street:en", "")
            suburb_raw = tags.get("addr:suburb", "") or tags.get("addr:city", "") or tags.get("addr:neighbourhood", "")
            street = clean_addr(street_raw)
            suburb = clean_addr(suburb_raw)
            address = ", ".join(filter(None, [street, suburb])) or "Cairo"

            dist = haversine_distance(lat, lon, el["lat"], el["lon"])

            restaurants.append({
                "id": f"OSM{i}",
                "name": name,
                "address": address,
                "lat": el["lat"],
                "lon": el["lon"],
                "category": category,
                "rating": 4.0,          # OSM has no ratings; shown as neutral
                "delivery_time": max(10, int(dist * 6)),   # rough estimate
                "fee": round(max(5, dist * 3), 0),
                "distance_km": round(dist, 2),
                "live": True,           # flag to show "Live" badge
            })

        return restaurants if restaurants else None

    except Exception:
        return None   # caller will fall back to static data


def filter_and_sort(restaurants, user_lat, user_lon, radius_km, sort_by):
    results = []
    for r in restaurants:
        dist = r.get("distance_km") or round(haversine_distance(user_lat, user_lon, r["lat"], r["lon"]), 2)
        if dist <= radius_km:
            results.append({**r, "distance_km": dist})
    if sort_by == "distance":
        results.sort(key=lambda x: x["distance_km"])
    elif sort_by == "rating":
        results.sort(key=lambda x: x["rating"], reverse=True)
    elif sort_by == "delivery_time":
        results.sort(key=lambda x: x["delivery_time"])
    return results


def find_closest_preset(lat, lon):
    best_name, best_dist = None, float("inf")
    for name, (plat, plon) in LOCATION_PRESETS.items():
        d = haversine_distance(lat, lon, plat, plon)
        if d < best_dist:
            best_dist, best_name = d, name
    return best_name


# ── Threads ───────────────────────────────────────────────────────────────────

class LocationFetchThread(QThread):
    location_found = pyqtSignal(float, float, str)
    location_error = pyqtSignal(str)

    def __init__(self, manual_coords=None, manual_name=None):
        super().__init__()
        self.manual_coords = manual_coords
        self.manual_name = manual_name

    def run(self):
        import time
        time.sleep(0.8)
        if self.manual_coords:
            self.location_found.emit(self.manual_coords[0], self.manual_coords[1], self.manual_name)
            return
        try:
            with urllib.request.urlopen("https://ipapi.co/json/", timeout=6) as r:
                data = json.loads(r.read().decode())
            lat = float(data["latitude"])
            lon = float(data["longitude"])
            # Use district/suburb if available, fall back to city
            city = (data.get("district") or data.get("city") or "Your Location")
            self.location_found.emit(lat, lon, city)
        except Exception:
            self.location_error.emit(
                "Could not detect location automatically. Please select one from the dropdown and click Use Selected."
            )


class RestaurantFetchThread(QThread):
    """Fetches live restaurants from OSM in background."""
    results_ready = pyqtSignal(list, bool)   # (restaurants, is_live)

    def __init__(self, lat, lon, radius_km):
        super().__init__()
        self.lat = lat
        self.lon = lon
        self.radius_km = radius_km

    def run(self):
        live = fetch_osm_restaurants(self.lat, self.lon, self.radius_km)
        if live:
            self.results_ready.emit(live, True)
        else:
            # Fall back to static data
            fallback = filter_and_sort(
                FALLBACK_RESTAURANTS, self.lat, self.lon, self.radius_km, "distance"
            )
            self.results_ready.emit(fallback, False)


# ── UI Widgets ────────────────────────────────────────────────────────────────

class RestaurantCard(QFrame):
    def __init__(self, restaurant, parent=None):
        super().__init__(parent)
        r = restaurant
        cat_color = CATEGORY_COLORS.get(r["category"], "#6b7280")

        self.setStyleSheet(f"""
            QFrame {{ background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px; }}
            QFrame:hover {{ border: 1.5px solid #f0b100; background: #fffdf0; }}
        """)
        self.setFixedHeight(148)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(14)

        badge = QLabel(r["category"])
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(72, 72)
        badge.setWordWrap(True)
        badge.setStyleSheet(f"""
            background: {cat_color}22; color: {cat_color}; border-radius: 10px;
            font-size: 10px; font-weight: 700; border: 1.5px solid {cat_color}55; padding: 4px;
        """)

        info = QVBoxLayout()
        info.setSpacing(2)

        # Name row with optional LIVE badge
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        name_lbl = QLabel(r["name"])
        name_lbl.setFont(QFont("Arial", 13, QFont.Bold))
        name_lbl.setStyleSheet("color: #111827; border: none; background: transparent;")
        name_row.addWidget(name_lbl)

        if r.get("live"):
            live_badge = QLabel("● LIVE")
            live_badge.setStyleSheet(
                "color: #10b981; font-size: 10px; font-weight: 700; border: none; background: transparent;"
            )
            name_row.addWidget(live_badge)
        name_row.addStretch()

        addr_lbl = QLabel(f"📌 {r.get('address', 'Cairo')}")
        addr_lbl.setStyleSheet("color: #9ca3af; font-size: 11px; border: none; background: transparent;")

        stars = "★" * int(r["rating"]) + ("½" if r["rating"] % 1 >= 0.5 else "")
        rating_text = f"{stars}  {r['rating']}" if not r.get("live") else "Not yet rated on Wasaly"
        rating_lbl = QLabel(rating_text)
        rating_lbl.setStyleSheet("color: #f59e0b; font-size: 12px; border: none; background: transparent;")

        meta_lbl = QLabel(
            f"🕐 ~{r['delivery_time']} min  ·  📍 {r['distance_km']} km away  ·  💳 EGP {r['fee']:.0f} est. delivery"
        )
        meta_lbl.setStyleSheet("color: #6b7280; font-size: 12px; border: none; background: transparent;")

        info.addLayout(name_row)
        info.addWidget(addr_lbl)
        info.addWidget(rating_lbl)
        info.addWidget(meta_lbl)

        btn = QPushButton("Order Now")
        btn.setFixedSize(100, 36)
        btn.setStyleSheet("""
            QPushButton { background: #f0b100; color: white; border: none;
                border-radius: 8px; font-size: 12px; font-weight: 700; }
            QPushButton:hover { background: #d99f00; }
        """)
        btn.clicked.connect(lambda: QMessageBox.information(
            self, "Coming Soon",
            f"Ordering from {r['name']} will be available in Sprint 2!"
        ))

        layout.addWidget(badge)
        layout.addLayout(info, stretch=1)
        layout.addWidget(btn, alignment=Qt.AlignVCenter)


# ── Main embedded widget ──────────────────────────────────────────────────────

class NearbyRestaurantsWidget(QWidget):
    """Embedded widget — no new window. Emits go_back on Back button press."""
    go_back = pyqtSignal()

    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.user_lat = None
        self.user_lon = None
        self.user_location_name = None
        self.location_thread = None
        self.fetch_thread = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet("background: #ffffff; border-bottom: 1px solid #e5e7eb;")
        header.setFixedHeight(64)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)

        back_btn = QPushButton("← Back")
        back_btn.setFixedHeight(36)
        back_btn.setStyleSheet("""
            QPushButton { background: #f3f4f6; color: #374151; border: none;
                border-radius: 8px; padding: 0 14px; font-size: 13px; font-weight: 600; }
            QPushButton:hover { background: #e5e7eb; }
        """)
        back_btn.clicked.connect(self.go_back.emit)

        title = QLabel("🍽  Discover Nearby Restaurants")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #111827;")

        user_lbl = QLabel(f"👤 {self.user_data.get('full_name', 'Customer')}")
        user_lbl.setStyleSheet("color: #6b7280; font-size: 13px;")

        hl.addWidget(back_btn)
        hl.addSpacing(12)
        hl.addWidget(title)
        hl.addStretch()
        hl.addWidget(user_lbl)
        root.addWidget(header)

        # Controls
        controls = QFrame()
        controls.setStyleSheet("background: #ffffff; border-bottom: 1px solid #e5e7eb;")
        cl = QHBoxLayout(controls)
        cl.setContentsMargins(24, 12, 24, 12)
        cl.setSpacing(10)

        cs = """
            QComboBox { border: 1px solid #d1d5db; border-radius: 8px;
                padding: 6px 10px; font-size: 13px; background: white; }
            QComboBox:focus { border: 2px solid #f0b100; }
        """

        loc_lbl = QLabel("📍 Location:")
        loc_lbl.setStyleSheet("color: #374151; font-weight: 600; font-size: 13px;")

        self.location_combo = QComboBox()
        self.location_combo.addItems(list(LOCATION_PRESETS.keys()))
        self.location_combo.setFixedWidth(220)
        self.location_combo.setStyleSheet(cs)

        self.detect_btn = QPushButton("📡  Auto-Detect (IP)")
        self.detect_btn.setFixedHeight(36)
        self.detect_btn.setStyleSheet("""
            QPushButton { background: #111827; color: white; border: none;
                border-radius: 8px; padding: 0 14px; font-size: 13px; font-weight: 600; }
            QPushButton:hover { background: #374151; }
            QPushButton:disabled { background: #9ca3af; }
        """)
        self.detect_btn.clicked.connect(self._detect_location)

        self.use_btn = QPushButton("✔  Use Selected")
        self.use_btn.setFixedHeight(36)
        self.use_btn.setStyleSheet("""
            QPushButton { background: #f0b100; color: white; border: none;
                border-radius: 8px; padding: 0 14px; font-size: 13px; font-weight: 600; }
            QPushButton:hover { background: #d99f00; }
            QPushButton:disabled { background: #9ca3af; }
        """)
        self.use_btn.clicked.connect(self._use_selected_location)

        r_lbl = QLabel("Radius:")
        r_lbl.setStyleSheet("color: #374151; font-size: 13px; font-weight: 600;")
        self.radius_combo = QComboBox()
        self.radius_combo.addItems(["2 km", "5 km", "10 km", "15 km", "20 km"])
        self.radius_combo.setCurrentIndex(2)
        self.radius_combo.setFixedWidth(90)
        self.radius_combo.setStyleSheet(cs)
        self.radius_combo.currentIndexChanged.connect(self._refresh_results)

        s_lbl = QLabel("Sort by:")
        s_lbl.setStyleSheet("color: #374151; font-size: 13px; font-weight: 600;")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Distance", "Rating", "Delivery Time"])
        self.sort_combo.setFixedWidth(130)
        self.sort_combo.setStyleSheet(cs)
        self.sort_combo.currentIndexChanged.connect(self._refresh_results)

        cl.addWidget(loc_lbl)
        cl.addWidget(self.location_combo)
        cl.addWidget(self.use_btn)
        cl.addWidget(self.detect_btn)
        cl.addSpacing(6)
        cl.addWidget(r_lbl)
        cl.addWidget(self.radius_combo)
        cl.addWidget(s_lbl)
        cl.addWidget(self.sort_combo)
        cl.addStretch()
        root.addWidget(controls)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(4)
        self.progress.setStyleSheet("""
            QProgressBar { background: #e5e7eb; border: none; }
            QProgressBar::chunk { background: #f0b100; }
        """)
        self.progress.hide()
        root.addWidget(self.progress)

        # Status
        self.status_label = QLabel("Select a location or click 'Detect My Location' to find nearby restaurants.")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            "color: #6b7280; font-size: 13px; padding: 12px; background: #f9fafb;"
        )
        root.addWidget(self.status_label)

        # Scroll results
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f9fafb; }")
        self.results_widget = QWidget()
        self.results_widget.setStyleSheet("background: #f9fafb;")
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setContentsMargins(24, 16, 24, 24)
        self.results_layout.setSpacing(12)
        self.results_layout.addStretch()
        scroll.setWidget(self.results_widget)
        root.addWidget(scroll, stretch=1)

    # ── Loading state ─────────────────────────
    def _set_loading(self, loading, msg=""):
        self.detect_btn.setEnabled(not loading)
        self.use_btn.setEnabled(not loading)
        self.detect_btn.setText("📡  Detecting…" if loading else "📡  Detect My Location")
        self.progress.setVisible(loading)
        if msg:
            self.status_label.setText(msg)
            self.status_label.setStyleSheet(
                "color: #6b7280; font-size: 13px; padding: 12px; background: #f9fafb;"
            )

    # ── Location ──────────────────────────────
    def _detect_location(self):
        self._set_loading(True, "Detecting your location via IP… (Note: IP detection is city-level — for best results, select your area manually)")
        self._clear_results()
        self.location_thread = LocationFetchThread()
        self.location_thread.location_found.connect(self._on_location_found)
        self.location_thread.location_error.connect(self._show_error)
        self.location_thread.start()

    def _use_selected_location(self):
        selected = self.location_combo.currentText()
        coords = LOCATION_PRESETS.get(selected)
        if not coords:
            self._show_error("Could not resolve selected location.")
            return
        self._set_loading(True, f"Loading restaurants near {selected}…")
        self._clear_results()
        self.location_thread = LocationFetchThread(manual_coords=coords, manual_name=selected)
        self.location_thread.location_found.connect(self._on_location_found)
        self.location_thread.location_error.connect(self._show_error)
        self.location_thread.start()

    def _on_location_found(self, lat, lon, name):
        self.user_lat, self.user_lon = lat, lon
        self._ip_based = not bool(self.location_thread.manual_coords)

        # Sync dropdown to closest preset
        closest = find_closest_preset(lat, lon)
        self.user_location_name = closest if closest else name
        if closest:
            idx = self.location_combo.findText(closest)
            if idx >= 0:
                self.location_combo.blockSignals(True)
                self.location_combo.setCurrentIndex(idx)
                self.location_combo.blockSignals(False)

        self._fetch_restaurants()

    def _show_error(self, msg):
        self._set_loading(False)
        self.status_label.setText(f"⚠️  {msg}")
        self.status_label.setStyleSheet(
            "color: #ef4444; font-size: 13px; padding: 12px; background: #f9fafb;"
        )

    # ── Live restaurant fetching ──────────────
    def _fetch_restaurants(self):
        radius = float(self.radius_combo.currentText().split()[0])
        self.status_label.setText(f"📡 Fetching live restaurants near {self.user_location_name}…")
        self.fetch_thread = RestaurantFetchThread(self.user_lat, self.user_lon, radius)
        self.fetch_thread.results_ready.connect(self._on_restaurants_ready)
        self.fetch_thread.start()

    def _on_restaurants_ready(self, restaurants, is_live):
        self._set_loading(False)
        self._current_restaurants = restaurants
        self._is_live = is_live
        self._render_results(restaurants, is_live)

    # ── Results ───────────────────────────────
    def _refresh_results(self):
        if self.user_lat is None:
            return
        # Re-fetch with new radius when radius changes
        self._fetch_restaurants()

    def _render_results(self, restaurants, is_live):
        radius = float(self.radius_combo.currentText().split()[0])

        # Apply sort
        sort_by = {"Distance": "distance", "Rating": "rating",
                   "Delivery Time": "delivery_time"}.get(self.sort_combo.currentText(), "distance")
        if sort_by == "distance":
            restaurants = sorted(restaurants, key=lambda x: x["distance_km"])
        elif sort_by == "rating":
            restaurants = sorted(restaurants, key=lambda x: x["rating"], reverse=True)
        elif sort_by == "delivery_time":
            restaurants = sorted(restaurants, key=lambda x: x["delivery_time"])

        self._clear_results()

        source_tag = "🟢 Live from OpenStreetMap" if is_live else "📋 Offline data"

        if not restaurants:
            lbl = QLabel(
                f"😕  No restaurants found within {radius:.0f} km of {self.user_location_name}.\n"
                f"Try increasing the radius."
            )
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #6b7280; font-size: 14px; padding: 40px;")
            self.results_layout.insertWidget(0, lbl)
            self.status_label.setText(
                f"📍 {self.user_location_name}  ·  No results within {radius:.0f} km  ·  {source_tag}"
            )
        else:
            ip_note = "  ·  ⚠️ IP location may be inaccurate — select your area manually for better results" if getattr(self, "_ip_based", False) else ""
            self.status_label.setText(
                f"📍 {self.user_location_name}  ·  {len(restaurants)} place(s) within {radius:.0f} km  ·  {source_tag}{ip_note}"
            )
            self.status_label.setStyleSheet(
                "color: #374151; font-size: 13px; padding: 12px; background: #f9fafb; font-weight: 600;"
            )
            for i, r in enumerate(restaurants):
                self.results_layout.insertWidget(i, RestaurantCard(r))

    def _clear_results(self):
        while self.results_layout.count() > 1:
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
