from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, jsonify
import sqlite3
import uuid
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "instance" / "accommodation.db"
UPLOAD_ROOT = BASE_DIR / "static" / "uploads"
ALLOWED_PHOTO_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_PHOTO_BYTES = 5 * 1024 * 1024
DEFAULT_COVER = "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?auto=format&fit=crop&w=900&q=80"

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key-in-production"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
APP_NAME = "HostelConnect"
APP_SLOGAN = "Premium Student Accommodation"

REGIONS = [
    "Greater Accra Region",
    "Ashanti Region",
    "Central Region",
    "Volta Region",
    "Northern Region",
    "Western Region",
    "Bono Region",
    "Upper East Region",
    "Upper West Region",
    "Eastern Region",
]

UNIVERSITIES = [
    {"name": "University of Ghana (Legon)", "region": "Greater Accra Region", "city": "Accra"},
    {"name": "Kwame Nkrumah University of Science and Technology (KNUST)", "region": "Ashanti Region", "city": "Kumasi"},
    {"name": "University of Cape Coast (UCC)", "region": "Central Region", "city": "Cape Coast"},
    {"name": "University of Education, Winneba (UEW)", "region": "Central Region", "city": "Winneba"},
    {"name": "University of Health and Allied Sciences (UHAS)", "region": "Volta Region", "city": "Ho"},
    {"name": "University for Development Studies (UDS)", "region": "Northern Region", "city": "Tamale"},
    {"name": "University of Mines and Technology (UMaT)", "region": "Western Region", "city": "Tarkwa"},
    {"name": "University of Energy and Natural Resources (UENR)", "region": "Bono Region", "city": "Sunyani"},
    {"name": "Ghana Institute of Management and Public Administration (GIMPA)", "region": "Greater Accra Region", "city": "Accra"},
    {"name": "C. K. Tedam University of Technology and Applied Sciences (CKT-UTAS)", "region": "Upper East Region", "city": "Navrongo"},
    {"name": "Simon Diedong Dombo University of Business and Integrated Development Studies (SDD-UBIDS)", "region": "Upper West Region", "city": "Wa"},
    {"name": "Accra Technical University", "region": "Greater Accra Region", "city": "Accra"},
    {"name": "Kumasi Technical University", "region": "Ashanti Region", "city": "Kumasi"},
    {"name": "Takoradi Technical University", "region": "Western Region", "city": "Takoradi"},
    {"name": "Ho Technical University", "region": "Volta Region", "city": "Ho"},
    {"name": "Cape Coast Technical University", "region": "Central Region", "city": "Cape Coast"},
    {"name": "Sunyani Technical University", "region": "Bono Region", "city": "Sunyani"},
    {"name": "Koforidua Technical University", "region": "Eastern Region", "city": "Koforidua"},
    {"name": "Tamale Technical University", "region": "Northern Region", "city": "Tamale"},
    {"name": "Bolgatanga Technical University", "region": "Upper East Region", "city": "Bolgatanga"},
    {"name": "Ashesi University", "region": "Eastern Region", "city": "Berekuso"},
    {"name": "Central University", "region": "Greater Accra Region", "city": "Miotso"},
    {"name": "Valley View University", "region": "Greater Accra Region", "city": "Oyibi"},
    {"name": "Presbyterian University College", "region": "Eastern Region", "city": "Abetifi"},
    {"name": "Methodist University College Ghana", "region": "Greater Accra Region", "city": "Accra"},
    {"name": "All Nations University", "region": "Eastern Region", "city": "Koforidua"},
    {"name": "Regent University College of Science and Technology", "region": "Greater Accra Region", "city": "Accra"},
    {"name": "Regional Maritime University", "region": "Greater Accra Region", "city": "Accra"},
    {"name": "Islamic University College, Ghana", "region": "Greater Accra Region", "city": "Accra"},
    {"name": "Ghana Christian University College", "region": "Greater Accra Region", "city": "Accra"},
    {"name": "Wisconsin International University College", "region": "Greater Accra Region", "city": "Accra"},
    {"name": "Data Link Institute", "region": "Greater Accra Region", "city": "Tema"},
    {"name": "Pentecost University", "region": "Greater Accra Region", "city": "Accra"},
    {"name": "Marshalls University College", "region": "Greater Accra Region", "city": "Accra"},
    {"name": "Garden City University", "region": "Ashanti Region", "city": "Kumasi"},
    {"name": "University of Professional Studies, Accra (UPSA)", "region": "Greater Accra Region", "city": "Accra"},
]

UNIVERSITY_NAMES = [u["name"] for u in UNIVERSITIES]
UNIVERSITIES_BY_REGION = {
    region: [u["name"] for u in UNIVERSITIES if u["region"] == region]
    for region in REGIONS
}
UNIVERSITY_LOOKUP = {u["name"]: u for u in UNIVERSITIES}

REGION_ALIASES = {
    "Greater Accra": "Greater Accra Region",
    "Ashanti": "Ashanti Region",
    "Central": "Central Region",
    "Eastern": "Eastern Region",
    "Western": "Western Region",
    "Volta": "Volta Region",
    "Northern": "Northern Region",
    "Upper East": "Upper East Region",
    "Upper West": "Upper West Region",
    "Bono": "Bono Region",
}


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _has_column(db, table, column):
    cols = [row[1] for row in db.execute(f"PRAGMA table_info({table})").fetchall()]
    return column in cols


def migrate_db(db):
    if not _has_column(db, "hostels", "university"):
        db.execute("ALTER TABLE hostels ADD COLUMN university TEXT")
    for column, definition in (
        ("source_url", "TEXT"),
        ("price_note", "TEXT"),
        ("is_directory", "INTEGER NOT NULL DEFAULT 0"),
    ):
        if not _has_column(db, "hostels", column):
            db.execute(f"ALTER TABLE hostels ADD COLUMN {column} {definition}")
    for column, definition in (
        ("room_label", "TEXT NOT NULL DEFAULT ''"),
        ("price_period", "TEXT NOT NULL DEFAULT 'month'"),
    ):
        if not _has_column(db, "rooms", column):
            db.execute(f"ALTER TABLE rooms ADD COLUMN {column} {definition}")
    for old, new in REGION_ALIASES.items():
        db.execute("UPDATE hostels SET region=? WHERE region=?", (new, old))
    db.execute(
        """UPDATE users SET email=REPLACE(email, '@staygh.local', '@hostelconnect.local')
           WHERE email LIKE '%@staygh.local'"""
    )
    db.commit()


def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student','manager','admin')),
        institution TEXT,
        phone TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS hostels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        manager_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        region TEXT NOT NULL,
        city TEXT NOT NULL,
        address TEXT,
        latitude REAL,
        longitude REAL,
        facilities TEXT,
        image_url TEXT,
        verified INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        university TEXT,
        source_url TEXT,
        price_note TEXT,
        is_directory INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(manager_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hostel_id INTEGER NOT NULL,
        room_type TEXT NOT NULL,
        price REAL NOT NULL,
        room_label TEXT NOT NULL DEFAULT '',
        price_period TEXT NOT NULL DEFAULT 'month',
        total_rooms INTEGER NOT NULL DEFAULT 1,
        available_rooms INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(hostel_id) REFERENCES hostels(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK(status IN ('pending','paid','cancelled')),
        payment_reference TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE,
        FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS favorites (
        student_id INTEGER NOT NULL,
        hostel_id INTEGER NOT NULL,
        PRIMARY KEY(student_id, hostel_id),
        FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(hostel_id) REFERENCES hostels(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hostel_id INTEGER NOT NULL,
        reporter_id INTEGER,
        reason TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        created_at TEXT NOT NULL,
        FOREIGN KEY(hostel_id) REFERENCES hostels(id) ON DELETE CASCADE,
        FOREIGN KEY(reporter_id) REFERENCES users(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER NOT NULL,
        hostel_id INTEGER,
        path TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(hostel_id) REFERENCES hostels(id) ON DELETE CASCADE
    );
    """)
    migrate_db(db)

    demo = [
        ("System Admin", "admin@hostelconnect.local", "admin123", "admin", None, "0200000000"),
        ("Demo Manager", "manager@hostelconnect.local", "manager123", "manager", "University of Ghana (Legon)", "0200000001"),
        ("Demo Student", "student@hostelconnect.local", "student123", "student", "University of Ghana (Legon)", "0200000002")
    ]
    for name, email, pw, role, institution, phone in demo:
        if not db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            db.execute("""INSERT INTO users
                (full_name,email,password_hash,role,institution,phone,created_at)
                VALUES (?,?,?,?,?,?,?)""",
                (name, email, generate_password_hash(pw), role, institution, phone, now()))
    db.commit()

    manager = db.execute("SELECT id FROM users WHERE email='manager@hostelconnect.local'").fetchone()
    if manager:
        seed_hostels(db, manager["id"])
    db.close()


def seed_hostels(db, manager_id):
    legacy_hostels = [
        ("Sunrise Hostel", "Comfortable student accommodation close to Legon campus.",
         "Greater Accra Region", "Accra", "Legon", "University of Ghana (Legon)",
         "Wi-Fi, Furnished, Security, Parking, Study Area",
         "https://images.unsplash.com/photo-1560185008-b033106af5c3?auto=format&fit=crop&w=900&q=80", 1,
         [("Single", 800, 20, 12), ("Double", 600, 15, 8), ("Shared", 450, 10, 5)]),
        ("Campus View Hostel", "Modern rooms a short ride from KNUST.",
         "Ashanti Region", "Kumasi", "Ayeduase", "Kwame Nkrumah University of Science and Technology (KNUST)",
         "Wi-Fi, AC, Laundry, Kitchen, Security",
         "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?auto=format&fit=crop&w=900&q=80", 1,
         [("Single", 750, 18, 10), ("Double", 550, 14, 6)]),
        ("Coastal Student Lodge", "Student-friendly rooms near UCC.",
         "Central Region", "Cape Coast", "Cape Coast", "University of Cape Coast (UCC)",
         "Wi-Fi, Water, Security, Study Area",
         "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=900&q=80", 1,
         [("Single", 650, 12, 7), ("Shared", 400, 10, 4)]),
        ("Winneba Garden Hostel", "Quiet lodge serving UEW students.",
         "Central Region", "Winneba", "North Campus Road", "University of Education, Winneba (UEW)",
         "Wi-Fi, Security, Kitchen, Study Area",
         "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=900&q=80", 1,
         [("Single", 580, 10, 5), ("Double", 430, 8, 3)]),
        ("Ho Health Lodge", "Rooms near UHAS for health science students.",
         "Volta Region", "Ho", "Sokode", "University of Health and Allied Sciences (UHAS)",
         "Wi-Fi, Water, Security, Study Area",
         "https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=900&q=80", 1,
         [("Single", 620, 8, 4), ("Shared", 380, 12, 8)]),
        ("Tamale Scholar Hostel", "Affordable rooms close to UDS.",
         "Northern Region", "Tamale", "Nyankpala Road", "University for Development Studies (UDS)",
         "Wi-Fi, Security, Water, Kitchen",
         "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=900&q=80", 1,
         [("Single", 500, 14, 9), ("Shared", 320, 16, 11)]),
        ("Tarkwa Miners Hostel", "Convenient stay for UMaT students.",
         "Western Region", "Tarkwa", "Campus Junction", "University of Mines and Technology (UMaT)",
         "Wi-Fi, Security, Parking, Water",
         "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=900&q=80", 1,
         [("Single", 700, 10, 6), ("Double", 480, 8, 2)]),
        ("Sunyani Energy Lodge", "Hostel near UENR with study spaces.",
         "Bono Region", "Sunyani", "Fiapre", "University of Energy and Natural Resources (UENR)",
         "Wi-Fi, Laundry, Security, Kitchen",
         "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=900&q=80", 1,
         [("Single", 560, 9, 5), ("Shared", 350, 10, 7)]),
        ("GIMPA Green Hostel", "Verified rooms around GIMPA.",
         "Greater Accra Region", "Accra", "Achimota", "Ghana Institute of Management and Public Administration (GIMPA)",
         "Wi-Fi, Furnished, Security, Study Area",
         "https://images.unsplash.com/photo-1560185127-6ed189bf61c9?auto=format&fit=crop&w=900&q=80", 1,
         [("Single", 900, 8, 3), ("Double", 680, 6, 2)]),
        ("Koforidua Tech Lodge", "Rooms for Koforidua Technical University students.",
         "Eastern Region", "Koforidua", "Poly Junction", "Koforidua Technical University",
         "Wi-Fi, Water, Security, Kitchen",
         "https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&w=900&q=80", 1,
         [("Single", 540, 12, 8), ("Shared", 330, 14, 10)]),
        ("Ashesi Hill Hostel", "Student housing near Ashesi University.",
         "Eastern Region", "Berekuso", "Berekuso Hills", "Ashesi University",
         "Wi-Fi, AC, Security, Study Area, Shuttle",
         "https://images.unsplash.com/photo-1502672023488-70e2348dfbdd?auto=format&fit=crop&w=900&q=80", 1,
         [("Single", 1200, 6, 2), ("Double", 850, 8, 4)]),
        ("Wa Scholars Court", "Available rooms close to SDD-UBIDS.",
         "Upper West Region", "Wa", "University Road", "Simon Diedong Dombo University of Business and Integrated Development Studies (SDD-UBIDS)",
         "Wi-Fi, Security, Water, Kitchen",
         "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?auto=format&fit=crop&w=900&q=80", 1,
         [("Single", 480, 10, 6), ("Shared", 300, 12, 9)]),
    ]
    existing = {row["name"]: row["id"] for row in db.execute("SELECT id, name FROM hostels").fetchall()}
    for index, item in enumerate(legacy_hostels, start=1):
        name, desc, region, city, address, university, facilities, image, verified, rooms = item
        if name not in existing:
            cur = db.execute(
                """INSERT INTO hostels
                (manager_id,name,description,region,city,address,university,facilities,image_url,verified,created_at,is_directory)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,0)""",
                (manager_id, name, desc, region, city, address, university, facilities, image, verified, now()),
            )
            hid = cur.lastrowid
            for room_type, price, total_rooms, available_rooms in rooms:
                db.execute(
                    "INSERT INTO rooms (hostel_id, room_type, price, total_rooms, available_rooms) VALUES (?, ?, ?, ?, ?)",
                    (hid, room_type, price, total_rooms, available_rooms),
                )
    ug_fee_source = "https://www.ug.edu.gh/aad/sites/academic.ug.edu.gh/files/2025-12/2025_26_Traditional_Halls_Fees.pdf"
    htu_source = "https://htu.edu.gh/2026-2027-fees-schedule/"
    gcu_source = "https://www.gcu.edu.gh/admissions/accommodation"
    listings = [
        {"name":"Frontline Apartment","image_url":"https://getrooms.co/wp-content/uploads/2022/10/frontline-apartment1-scaled-1.jpg","description":"Student accommodation in Ayeduase near KNUST. The provider lists shared rooms with en-suite facilities, Wi-Fi, and a shared kitchen with free gas.","region":"Ashanti Region","city":"Kumasi","address":"Ayeduase, near KNUST","university":"Kwame Nkrumah University of Science and Technology (KNUST)","facilities":"En suite, Wi-Fi, Shared kitchen, Free gas","source_url":"https://frontlinehostel.com/room-prices/","price_note":"Provider's published 2026/27 academic-year rates. The 3-in-1 option is limited; check current availability and eligibility with Frontline.","rooms":[("Shared","3-in-1",4300,"per academic year"),("Shared","4-in-1",3600,"per academic year")]},
        {"name":"Legon Hall","description":"University of Ghana traditional residence. Published rates below are the local-student charges from the university's 2025/26 schedule; newer rates were not available in the source checked.","region":"Greater Accra Region","city":"Accra","address":"University of Ghana, Legon","university":"University of Ghana (Legon)","facilities":"University residence, Shared facility","source_url":ug_fee_source,"price_note":"Official UG schedule for 2025/26: GH₵1,250 per semester for local freshers and GH₵1,125 for continuing local students. Confirm 2026/27 rates and bed allocation with UG.","rooms":[("Shared","Local fresher rate",1250,"per semester (2025/26)"),("Shared","Continuing local rate",1125,"per semester (2025/26)")]},
        {"name":"Akuafo Hall","image_url":"https://univers.ug.edu.gh/storage/2023/03/photo1677878971-1.jpeg","description":"University of Ghana traditional residence. Published rates below are the local-student charges from the university's 2025/26 schedule; newer rates were not available in the source checked.","region":"Greater Accra Region","city":"Accra","address":"University of Ghana, Legon","university":"University of Ghana (Legon)","facilities":"University residence, Shared facility","source_url":ug_fee_source,"price_note":"Official UG schedule for 2025/26: GH₵1,250 per semester for local freshers and GH₵1,125 for continuing local students. Confirm 2026/27 rates and bed allocation with UG.","rooms":[("Shared","Local fresher rate",1250,"per semester (2025/26)"),("Shared","Continuing local rate",1125,"per semester (2025/26)")]},
        {"name":"Commonwealth Hall","image_url":"https://www.ug.edu.gh/sites/default/files/2024-06/0J9A8523.jpg","description":"University of Ghana traditional residence. Published rates below are the local-student charges from the university's 2025/26 schedule; newer rates were not available in the source checked.","region":"Greater Accra Region","city":"Accra","address":"University of Ghana, Legon","university":"University of Ghana (Legon)","facilities":"University residence, Shared facility","source_url":ug_fee_source,"price_note":"Official UG schedule for 2025/26: GH₵1,250 per semester for local freshers and GH₵1,125 for continuing local students. Confirm 2026/27 rates and bed allocation with UG.","rooms":[("Shared","Local fresher rate",1250,"per semester (2025/26)"),("Shared","Continuing local rate",1125,"per semester (2025/26)")]},
        {"name":"Volta Hall","description":"University of Ghana traditional residence. Published rates below are the local-student charges from the university's 2025/26 schedule; newer rates were not available in the source checked.","region":"Greater Accra Region","city":"Accra","address":"University of Ghana, Legon","university":"University of Ghana (Legon)","facilities":"University residence, Shared facility","source_url":ug_fee_source,"price_note":"Official UG schedule for 2025/26: GH₵1,250 per semester for local freshers and GH₵1,125 for continuing local students. Confirm 2026/27 rates and bed allocation with UG.","rooms":[("Shared","Local fresher rate",1250,"per semester (2025/26)"),("Shared","Continuing local rate",1125,"per semester (2025/26)")]},
        {"name":"Mensah Sarbah Hall","image_url":"https://msh.ug.edu.gh/wp-content/uploads/2023/11/1-1.png","description":"University of Ghana traditional residence. Published rates below are the local-student charges from the university's 2025/26 schedule; newer rates were not available in the source checked.","region":"Greater Accra Region","city":"Accra","address":"University of Ghana, Legon","university":"University of Ghana (Legon)","facilities":"University residence, Shared facility","source_url":ug_fee_source,"price_note":"Official UG schedule for 2025/26: GH₵1,250 per semester for local freshers and GH₵1,125 for continuing local students. Confirm 2026/27 rates and bed allocation with UG.","rooms":[("Shared","Local fresher rate",1250,"per semester (2025/26)"),("Shared","Continuing local rate",1125,"per semester (2025/26)")]},
        {"name":"Acolatse Hall","description":"Ho Technical University residence. HTU publishes this fee for the 2026/27 academic year and provides booking through its student accommodation system.","region":"Volta Region","city":"Ho","address":"Ho Technical University campus","university":"Ho Technical University","facilities":"University residence, On-campus","source_url":htu_source,"price_note":"Official HTU 2026/27 accommodation fee schedule.","rooms":[("Shared","Hall accommodation",2170,"per academic year")]},
        {"name":"Vodzi Hall","description":"Ho Technical University residence. HTU publishes this fee for the 2026/27 academic year and provides booking through its student accommodation system.","region":"Volta Region","city":"Ho","address":"Ho Technical University campus","university":"Ho Technical University","facilities":"University residence, On-campus","source_url":htu_source,"price_note":"Official HTU 2026/27 accommodation fee schedule.","rooms":[("Shared","Hall accommodation",2170,"per academic year")]},
        {"name":"GETFund Hostel","description":"Ho Technical University residence. The 2026/27 schedule lists separate large and small four-person rooms and six-person rooms.","region":"Volta Region","city":"Ho","address":"Ho Technical University campus","university":"Ho Technical University","facilities":"University residence, On-campus","source_url":htu_source,"price_note":"Official HTU 2026/27 accommodation fee schedule; male and female options are listed at the same rate.","rooms":[("Shared","4-in-1, large",2600,"per academic year"),("Shared","4-in-1, small",2300,"per academic year"),("Shared","6-in-1",2170,"per academic year")]},
        {"name":"Defiat Hostel","description":"Ho Technical University hostel. HTU lists the four-person room rate for 2026/27.","region":"Volta Region","city":"Ho","address":"Ho Technical University","university":"Ho Technical University","facilities":"Student hostel","source_url":htu_source,"price_note":"Official HTU 2026/27 accommodation fee schedule; listed rate is for four occupants.","rooms":[("Shared","4-in-1",4000,"per academic year")]},
        {"name":"Albert Acquah Hall","description":"Garden City University on-campus residence. The university publishes annual rates for one-, two-, three-, and four-person rooms.","region":"Ashanti Region","city":"Kumasi","address":"Garden City University","university":"Garden City University","facilities":"Air conditioning, Internet, Study rooms, DSTV, Wardrobes","source_url":gcu_source,"price_note":"Official Garden City University rates for the 2026/27 academic year.","rooms":[("Single","1 person",12000,"per academic year"),("Double","2 people",6000,"per academic year"),("Shared","3 people",4500,"per academic year"),("Shared","4 people",3500,"per academic year")]},
        {"name":"Lawyer Antwi Trinity Hall","description":"Garden City University on-campus residence with private facilities, internet access, security, and common rooms.","region":"Ashanti Region","city":"Kumasi","address":"Garden City University","university":"Garden City University","facilities":"Private facilities, Internet, 24/7 security, Common rooms","source_url":gcu_source,"price_note":"Official Garden City University rate for the 2026/27 academic year.","rooms":[("Double","2 people",6500,"per academic year")]},
        {"name":"Sarki Hostel","description":"Garden City University on-campus hostel with water supply, 24/7 power, and a secure student community.","region":"Ashanti Region","city":"Kumasi","address":"Garden City University","university":"Garden City University","facilities":"Water supply, 24/7 power, Secure environment","source_url":gcu_source,"price_note":"Official Garden City University rates for the 2026/27 academic year.","rooms":[("Single","1 person",8000,"per academic year"),("Double","2 people",4000,"per academic year")]},
        {"name":"Godfrey Hostel","description":"Private hostel in Kwaprow, about one kilometre from the University of Cape Coast. The provider lists per-person annual prices and facilities on its website.","region":"Central Region","city":"Cape Coast","address":"Kwaprow, about 1 km from UCC","university":"University of Cape Coast (UCC)","facilities":"Water, Electricity, Kitchenette, Parking, Standby generator, DSTV","source_url":"https://godfreyhostelucc.com/","price_note":"Rates currently published by the hostel as per-person prices per annum. Confirm the applicable academic year and room availability directly with the provider.","rooms":[("Shared","4-bed room, per person",3000,"per annum"),("Shared","3-person room, per person",3000,"per annum"),("Double","2-person twin room, per person",4500,"per annum"),("Single","1 person",5500,"per annum")]},
    ]
    listings.extend([
        {"name":"UPSA Hostel A","description":"University of Professional Studies, Accra residence. Students apply through the university hostel system; an application does not guarantee bed allocation.","region":"Greater Accra Region","city":"Accra","address":"UPSA campus, Accra","university":"University of Professional Studies, Accra (UPSA)","facilities":"University residence, Student application and allocation","source_url":"https://upsa.edu.gh/opening-of-hostel-application-portal-for-continuing-students-first-semester-2025-26-academic-year/","price_note":"Official UPSA first-semester 2025/26 notice. Totals include hall dues and a refundable GH₵200 damage deposit. Confirm current-year rates and bed allocation with UPSA.","rooms":[("Shared","4-in-1; total includes refundable deposit",2070,"per semester (2025/26)"),("Double","2-in-1; total includes refundable deposit",5700,"per semester (2025/26)")]},
        {"name":"Matthew Opoku Prempeh Hostel","image_url":"https://metrotvonline.com/wp-content/uploads/2024/11/IMG-20241119-WA0055.jpg","description":"UPSA university residence. The university's hostel notice says students apply through the hostel administration and pay only after allocation.","region":"Greater Accra Region","city":"Accra","address":"UPSA campus, Accra","university":"University of Professional Studies, Accra (UPSA)","facilities":"University residence, Student application and allocation","source_url":"https://upsa.edu.gh/opening-of-hostel-application-portal-for-continuing-students-first-semester-2025-26-academic-year/","price_note":"Official UPSA first-semester 2025/26 notice. Totals include hall dues and a refundable GH₵200 damage deposit. Confirm current-year rates and bed allocation with UPSA.","rooms":[("Shared","4-in-1; total includes refundable deposit",2510,"per semester (2025/26)"),("Double","2-in-1; total includes refundable deposit",6995,"per semester (2025/26)")]},
        {"name":"Amon Kotei Hostel","image_url":"https://www.ghanabusinessnews.com/wp-content/uploads/2023/03/UPSA-hostel.jpg","description":"UPSA university residence listed in the university's hostel fee and reservation notice.","region":"Greater Accra Region","city":"Accra","address":"UPSA campus, Accra","university":"University of Professional Studies, Accra (UPSA)","facilities":"University residence, Student application and allocation","source_url":"https://upsa.edu.gh/opening-of-hostel-application-portal-for-continuing-students-first-semester-2025-26-academic-year/","price_note":"Official UPSA first-semester 2025/26 notice. Totals include hall dues and a refundable GH₵200 damage deposit. Confirm current-year rates and bed allocation with UPSA.","rooms":[("Shared","4-in-1; total includes refundable deposit",2620,"per semester (2025/26)"),("Double","2-in-1; total includes refundable deposit",7105,"per semester (2025/26)")]}
    ])
    for listing in listings:
        existing = db.execute("SELECT id FROM hostels WHERE name=?", (listing["name"],)).fetchone()
        fields = (listing["description"],listing["region"],listing["city"],listing["address"],listing["university"],listing["facilities"],listing.get("image_url"),listing["source_url"],listing["price_note"])
        if existing:
            hostel_id=existing["id"]
            db.execute("""UPDATE hostels SET description=?,region=?,city=?,address=?,university=?,facilities=?,image_url=?,source_url=?,price_note=?,verified=1,is_directory=1 WHERE id=?""",( *fields,hostel_id))
            db.execute("DELETE FROM rooms WHERE hostel_id=?",(hostel_id,))
        else:
            cur=db.execute("""INSERT INTO hostels (manager_id,name,description,region,city,address,university,facilities,image_url,verified,created_at,source_url,price_note,is_directory) VALUES(?,?,?,?,?,?,?,?,?,1,?,?,?,1)""",(manager_id,listing["name"],*fields[:7],now(),*fields[7:]))
            hostel_id=cur.lastrowid
        for room_type,room_label,price,period in listing["rooms"]:
            db.execute("""INSERT INTO rooms (hostel_id,room_type,room_label,price,price_period,total_rooms,available_rooms) VALUES(?,?,?,?,?,0,0)""",(hostel_id,room_type,room_label,price,period))
    db.commit()


def now():
    return datetime.utcnow().isoformat(timespec="seconds")


def media_url(path):
    if not path:
        return DEFAULT_COVER
    if str(path).startswith("http"):
        return path
    return url_for("static", filename=path)


def save_uploaded_photos(files):
    saved = []
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    for storage in files:
        if not storage or not getattr(storage, "filename", ""):
            continue
        ext = Path(storage.filename).suffix.lower()
        if ext not in ALLOWED_PHOTO_EXT:
            flash(f"Skipped {storage.filename}. Use JPG, PNG, WEBP or GIF.", "warning")
            continue
        data = storage.read()
        if not data:
            continue
        if len(data) > MAX_PHOTO_BYTES:
            flash(f"Skipped {storage.filename}. Each photo must be 5MB or smaller.", "warning")
            continue
        filename = f"{uuid.uuid4().hex}{ext}"
        dest = UPLOAD_ROOT / filename
        dest.write_bytes(data)
        saved.append(f"uploads/{filename}")
    return saved


def store_photos(db, owner_id, files, hostel_id=None):
    paths = save_uploaded_photos(files)
    for path in paths:
        db.execute(
            "INSERT INTO photos(owner_id,hostel_id,path,created_at) VALUES(?,?,?,?)",
            (owner_id, hostel_id, path, now()),
        )
    if paths and hostel_id:
        db.execute("UPDATE hostels SET image_url=? WHERE id=?", (paths[0], hostel_id))
    return paths


def delete_photo_file(path):
    if not path or str(path).startswith("http"):
        return
    file_path = BASE_DIR / "static" / path
    if file_path.is_file() and UPLOAD_ROOT in file_path.resolve().parents:
        file_path.unlink(missing_ok=True)


@app.context_processor
def inject_globals():
    return {
        "regions": REGIONS,
        "universities": UNIVERSITY_NAMES,
        "universities_by_region": UNIVERSITIES_BY_REGION,
        "current_user": current_user(),
        "app_name": APP_NAME,
        "app_slogan": APP_SLOGAN,
        "media_url": media_url,
    }


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    db.close()
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please sign in first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                flash("Please sign in first.", "warning")
                return redirect(url_for("login"))
            if user["role"] not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


@app.route("/")
def index():
    db = get_db()
    region = request.args.get("region", "")
    university = request.args.get("university", "")
    q = request.args.get("q", "")
    room_type = request.args.get("room_type", "")
    max_price = request.args.get("max_price", "")
    sql = """SELECT h.*, MIN(r.price) min_price, MIN(r.price_period) price_period, SUM(r.available_rooms) available_rooms
             FROM hostels h LEFT JOIN rooms r ON r.hostel_id=h.id WHERE h.verified=1"""
    params = []
    if region:
        sql += " AND h.region=?"; params.append(region)
    if university:
        sql += " AND h.university=?"; params.append(university)
    if q:
        sql += " AND (h.name LIKE ? OR h.city LIKE ? OR h.address LIKE ? OR IFNULL(h.university,'') LIKE ?)"
        like = f"%{q}%"; params += [like, like, like, like]
    sql += " GROUP BY h.id"
    having = []
    having_params = []
    if room_type:
        having.append("SUM(CASE WHEN r.room_type=? THEN 1 ELSE 0 END)>0")
        having_params.append(room_type)
    if max_price:
        try:
            if room_type:
                having.append("MIN(CASE WHEN r.room_type=? THEN r.price END) <= ?")
                having_params.extend([room_type, float(max_price)])
            else:
                having.append("MIN(r.price) <= ?")
                having_params.append(float(max_price))
        except ValueError:
            pass
    if university or region:
        having.append("(COALESCE(SUM(r.available_rooms),0) > 0 OR MAX(h.is_directory)=1)")
    if having:
        sql += " HAVING " + " AND ".join(having)
        params += having_params
    sql += " ORDER BY available_rooms DESC, h.created_at DESC"
    hostels = db.execute(sql, params).fetchall()
    db.close()
    selected_uni = UNIVERSITY_LOOKUP.get(university)
    return render_template(
        "index.html",
        hostels=hostels,
        q=q,
        selected_region=region,
        selected_university=university,
        selected_uni=selected_uni,
        room_type=room_type,
        max_price=max_price,
    )


@app.route("/api/universities")
def api_universities():
    region = request.args.get("region", "")
    if region:
        names = UNIVERSITIES_BY_REGION.get(region, [])
    else:
        names = UNIVERSITY_NAMES
    return jsonify({"universities": names})


@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form["full_name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        role = request.form.get("role", "student")
        institution = request.form.get("institution", "")
        phone = request.form.get("phone", "")
        if role not in ("student","manager"):
            role = "student"
        db = get_db()
        try:
            cur = db.execute("""INSERT INTO users
                (full_name,email,password_hash,role,institution,phone,created_at)
                VALUES(?,?,?,?,?,?,?)""",
                (name,email,generate_password_hash(password),role,institution,phone,now()))
            db.commit()
            session["user_id"] = cur.lastrowid
            flash("Account created successfully.", "success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("That email is already registered.", "danger")
        finally:
            db.close()
    return render_template("register.html")


@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        db.close()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash("Welcome back.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("index"))


@app.route("/hostel/<int:hostel_id>")
def hostel_detail(hostel_id):
    db = get_db()
    hostel = db.execute("""SELECT h.*, u.full_name manager_name
                           FROM hostels h JOIN users u ON u.id=h.manager_id
                           WHERE h.id=?""", (hostel_id,)).fetchone()
    rooms = db.execute("SELECT * FROM rooms WHERE hostel_id=? ORDER BY price", (hostel_id,)).fetchall()
    photos = db.execute("SELECT * FROM photos WHERE hostel_id=? ORDER BY created_at DESC", (hostel_id,)).fetchall()
    db.close()
    if not hostel: abort(404)
    return render_template("hostel_detail.html", hostel=hostel, rooms=rooms, photos=photos)


@app.route("/favorite/<int:hostel_id>", methods=["POST"])
@login_required
@role_required("student")
def favorite(hostel_id):
    db = get_db()
    exists = db.execute("SELECT 1 FROM favorites WHERE student_id=? AND hostel_id=?",
                        (session["user_id"],hostel_id)).fetchone()
    if exists:
        db.execute("DELETE FROM favorites WHERE student_id=? AND hostel_id=?",
                   (session["user_id"],hostel_id))
    else:
        db.execute("INSERT OR IGNORE INTO favorites(student_id,hostel_id) VALUES(?,?)",
                   (session["user_id"],hostel_id))
    db.commit(); db.close()
    return redirect(request.referrer or url_for("index"))


@app.route("/book/<int:room_id>", methods=["POST"])
@login_required
@role_required("student")
def book(room_id):
    db = get_db()
    room = db.execute("""SELECT r.*, h.is_directory, h.id hostel_id FROM rooms r JOIN hostels h ON h.id=r.hostel_id WHERE r.id=?""", (room_id,)).fetchone()
    if not room: abort(404)
    if room["is_directory"]:
        ref = f"REQ-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{session['user_id']}"
        db.execute("""INSERT INTO bookings(room_id,student_id,amount,status,payment_reference,created_at)
                      VALUES(?,?,?,?,?,?)""",
                   (room_id,session["user_id"],room["price"],"pending",ref,now()))
        db.commit()
        db.close()
        flash("Your on-site booking request was sent. It will remain pending until the listing owner confirms availability; no payment has been taken.", "success")
        return redirect(url_for("dashboard"))
    if room["available_rooms"] <= 0:
        flash("That room type is currently unavailable.", "danger")
        db.close(); return redirect(request.referrer or url_for("index"))
    ref = f"DEMO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{session['user_id']}"
    db.execute("""INSERT INTO bookings(room_id,student_id,amount,status,payment_reference,created_at)
                  VALUES(?,?,?,?,?,?)""",
               (room_id,session["user_id"],room["price"],"paid",ref,now()))
    db.execute("UPDATE rooms SET available_rooms=available_rooms-1 WHERE id=?", (room_id,))
    db.commit(); db.close()
    flash("Demo payment recorded and room reserved. Replace this with a real payment gateway before deployment.", "success")
    return redirect(url_for("dashboard"))


@app.route("/report/<int:hostel_id>", methods=["POST"])
@login_required
def report(hostel_id):
    reason = request.form.get("reason","").strip()
    if reason:
        db = get_db()
        db.execute("""INSERT INTO reports(hostel_id,reporter_id,reason,created_at)
                      VALUES(?,?,?,?)""", (hostel_id,session["user_id"],reason,now()))
        db.commit(); db.close()
        flash("Report submitted to administrators.", "success")
    return redirect(url_for("hostel_detail", hostel_id=hostel_id))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    if user["role"] == "admin":
        return redirect(url_for("admin_dashboard"))
    if user["role"] == "manager":
        return redirect(url_for("manager_dashboard"))
    db = get_db()
    bookings = db.execute("""SELECT b.*, r.room_type, r.price, h.name hostel_name
                             FROM bookings b JOIN rooms r ON r.id=b.room_id
                             JOIN hostels h ON h.id=r.hostel_id
                             WHERE b.student_id=? ORDER BY b.created_at DESC""",
                          (user["id"],)).fetchall()
    favorites = db.execute("""SELECT h.* FROM favorites f JOIN hostels h ON h.id=f.hostel_id
                              WHERE f.student_id=?""", (user["id"],)).fetchall()
    photos = db.execute("""SELECT * FROM photos WHERE owner_id=? AND hostel_id IS NULL
                           ORDER BY created_at DESC""", (user["id"],)).fetchall()
    db.close()
    return render_template("student_dashboard.html", bookings=bookings, favorites=favorites, photos=photos)


@app.route("/manager")
@login_required
@role_required("manager")
def manager_dashboard():
    db = get_db()
    hostels = db.execute("SELECT * FROM hostels WHERE manager_id=? ORDER BY created_at DESC",
                         (session["user_id"],)).fetchall()
    stats = db.execute("""SELECT COUNT(*) listings,
                                 COALESCE(SUM(r.total_rooms),0) total_rooms,
                                 COALESCE(SUM(r.available_rooms),0) available_rooms
                          FROM hostels h LEFT JOIN rooms r ON r.hostel_id=h.id
                          WHERE h.manager_id=?""", (session["user_id"],)).fetchone()
    transactions = db.execute("""SELECT b.*, u.full_name student_name, u.institution,
                                        r.room_type, h.name hostel_name
                                 FROM bookings b JOIN users u ON u.id=b.student_id
                                 JOIN rooms r ON r.id=b.room_id JOIN hostels h ON h.id=r.hostel_id
                                 WHERE h.manager_id=? ORDER BY b.created_at DESC LIMIT 20""",
                              (session["user_id"],)).fetchall()
    photos = db.execute("""SELECT * FROM photos WHERE owner_id=? AND hostel_id IS NULL
                           ORDER BY created_at DESC""", (session["user_id"],)).fetchall()
    hostel_photos = db.execute("""SELECT p.* FROM photos p JOIN hostels h ON h.id=p.hostel_id
                                  WHERE h.manager_id=? ORDER BY p.created_at DESC""",
                               (session["user_id"],)).fetchall()
    photos_by_hostel = {}
    for photo in hostel_photos:
        photos_by_hostel.setdefault(photo["hostel_id"], []).append(photo)
    db.close()
    return render_template("manager_dashboard.html", hostels=hostels, stats=stats,
                           transactions=transactions, photos=photos, photos_by_hostel=photos_by_hostel)


@app.route("/manager/hostel/new", methods=["GET","POST"])
@login_required
@role_required("manager", "admin")
def new_hostel():
    if request.method == "POST":
        university = request.form.get("university", "")
        region = request.form.get("region", "")
        uni = UNIVERSITY_LOOKUP.get(university)
        if uni:
            region = uni["region"]
        db = get_db()
        cur = db.execute("""INSERT INTO hostels
            (manager_id,name,description,region,city,address,university,facilities,image_url,verified,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (session["user_id"],request.form["name"],request.form["description"],
             region,request.form["city"],request.form["address"],university,
             request.form["facilities"], None,
             1 if current_user()["role"] == "admin" else 0, now()))
        hid = cur.lastrowid
        store_photos(db, session["user_id"], request.files.getlist("photos"), hostel_id=hid)
        db.execute("""INSERT INTO rooms(hostel_id,room_type,price,total_rooms,available_rooms)
                      VALUES(?,?,?,?,?)""",
                   (hid,request.form["room_type"],float(request.form["price"]),
                    int(request.form["total_rooms"]),int(request.form["available_rooms"])))
        db.commit(); db.close()
        if current_user()["role"] == "admin":
            flash("Listing added and published.", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Listing submitted. It must be approved by an administrator.", "success")
        return redirect(url_for("manager_dashboard"))
    return render_template("hostel_form.html", hostel=None)


@app.route("/manager/hostel/<int:hostel_id>/rooms", methods=["POST"])
@login_required
@role_required("manager")
def add_room(hostel_id):
    db = get_db()
    owned = db.execute("SELECT 1 FROM hostels WHERE id=? AND manager_id=?",
                       (hostel_id,session["user_id"])).fetchone()
    if not owned: abort(403)
    db.execute("""INSERT INTO rooms(hostel_id,room_type,price,total_rooms,available_rooms)
                  VALUES(?,?,?,?,?)""",
               (hostel_id,request.form["room_type"],float(request.form["price"]),
                int(request.form["total_rooms"]),int(request.form["available_rooms"])))
    db.commit(); db.close()
    return redirect(url_for("manager_dashboard"))


@app.route("/manager/room/<int:room_id>/update", methods=["POST"])
@login_required
@role_required("manager")
def update_room(room_id):
    db = get_db()
    room = db.execute("""SELECT r.* FROM rooms r JOIN hostels h ON h.id=r.hostel_id
                         WHERE r.id=? AND h.manager_id=?""", (room_id,session["user_id"])).fetchone()
    if not room: abort(403)
    total = int(request.form["total_rooms"])
    available = min(max(int(request.form["available_rooms"]),0),total)
    price = float(request.form["price"])
    db.execute("UPDATE rooms SET price=?,total_rooms=?,available_rooms=? WHERE id=?",
               (price,total,available,room_id))
    db.commit(); db.close()
    flash("Room availability and price updated.", "success")
    return redirect(url_for("manager_dashboard"))


@app.route("/photos/upload", methods=["POST"])
@login_required
def upload_my_photos():
    db = get_db()
    saved = store_photos(db, session["user_id"], request.files.getlist("photos"))
    db.commit(); db.close()
    if saved:
        flash(f"{len(saved)} photo(s) uploaded.", "success")
    else:
        flash("Choose one or more pictures to upload.", "warning")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/manager/hostel/<int:hostel_id>/photos", methods=["POST"])
@login_required
@role_required("manager", "admin")
def upload_hostel_photos(hostel_id):
    user = current_user()
    db = get_db()
    hostel = db.execute("SELECT * FROM hostels WHERE id=?", (hostel_id,)).fetchone()
    if not hostel:
        db.close(); abort(404)
    if user["role"] != "admin" and hostel["manager_id"] != user["id"]:
        db.close(); abort(403)
    saved = store_photos(db, user["id"], request.files.getlist("photos"), hostel_id=hostel_id)
    db.commit(); db.close()
    if saved:
        flash(f"{len(saved)} hostel photo(s) uploaded.", "success")
    else:
        flash("Choose one or more pictures to upload.", "warning")
    if user["role"] == "admin":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("manager_dashboard"))


@app.route("/photos/<int:photo_id>/delete", methods=["POST"])
@login_required
def delete_photo(photo_id):
    user = current_user()
    db = get_db()
    photo = db.execute("SELECT * FROM photos WHERE id=?", (photo_id,)).fetchone()
    if not photo:
        db.close(); abort(404)
    allowed = photo["owner_id"] == user["id"] or user["role"] == "admin"
    if photo["hostel_id"] and user["role"] == "manager":
        owned = db.execute("SELECT 1 FROM hostels WHERE id=? AND manager_id=?",
                           (photo["hostel_id"], user["id"])).fetchone()
        allowed = allowed or bool(owned)
    if not allowed:
        db.close(); abort(403)
    delete_photo_file(photo["path"])
    db.execute("DELETE FROM photos WHERE id=?", (photo_id,))
    db.commit(); db.close()
    flash("Photo removed.", "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.errorhandler(413)
def too_large(e):
    flash("Those files are too large. Please upload smaller pictures.", "danger")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/admin")
@login_required
@role_required("admin")
def admin_dashboard():
    db = get_db()
    stats = {
        "users": db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
        "students": db.execute("SELECT COUNT(*) c FROM users WHERE role='student'").fetchone()["c"],
        "managers": db.execute("SELECT COUNT(*) c FROM users WHERE role='manager'").fetchone()["c"],
        "listings": db.execute("SELECT COUNT(*) c FROM hostels").fetchone()["c"],
        "verified": db.execute("SELECT COUNT(*) c FROM hostels WHERE verified=1").fetchone()["c"],
        "reports": db.execute("SELECT COUNT(*) c FROM reports WHERE status='open'").fetchone()["c"],
        "revenue": db.execute("SELECT COALESCE(SUM(amount),0) c FROM bookings WHERE status='paid'").fetchone()["c"]
    }
    pending = db.execute("""SELECT h.*, u.full_name manager_name, u.email manager_email
                            FROM hostels h JOIN users u ON u.id=h.manager_id
                            WHERE h.verified=0 ORDER BY h.created_at DESC""").fetchall()
    reports = db.execute("""SELECT r.*, h.name hostel_name, u.full_name reporter_name
                            FROM reports r JOIN hostels h ON h.id=r.hostel_id
                            LEFT JOIN users u ON u.id=r.reporter_id
                            WHERE r.status='open' ORDER BY r.created_at DESC""").fetchall()
    photos = db.execute("""SELECT * FROM photos WHERE owner_id=? AND hostel_id IS NULL
                           ORDER BY created_at DESC""", (session["user_id"],)).fetchall()
    hostels = db.execute("""SELECT h.*, u.full_name manager_name
                            FROM hostels h JOIN users u ON u.id=h.manager_id
                            ORDER BY h.created_at DESC""").fetchall()
    hostel_photos = db.execute("SELECT * FROM photos WHERE hostel_id IS NOT NULL ORDER BY created_at DESC").fetchall()
    photos_by_hostel = {}
    for photo in hostel_photos:
        photos_by_hostel.setdefault(photo["hostel_id"], []).append(photo)
    db.close()
    return render_template("admin_dashboard.html", stats=stats, pending=pending, reports=reports,
                           photos=photos, hostels=hostels, photos_by_hostel=photos_by_hostel)


@app.route("/admin/hostel/<int:hostel_id>/verify", methods=["POST"])
@login_required
@role_required("admin")
def verify_hostel(hostel_id):
    db = get_db()
    db.execute("UPDATE hostels SET verified=1 WHERE id=?", (hostel_id,))
    db.commit(); db.close()
    flash("Accommodation listing approved.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/hostel/<int:hostel_id>/remove", methods=["POST"])
@login_required
@role_required("admin")
def remove_hostel(hostel_id):
    db = get_db()
    db.execute("DELETE FROM hostels WHERE id=?", (hostel_id,))
    db.commit(); db.close()
    flash("Listing removed.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/report/<int:report_id>/close", methods=["POST"])
@login_required
@role_required("admin")
def close_report(report_id):
    db = get_db()
    db.execute("UPDATE reports SET status='closed' WHERE id=?", (report_id,))
    db.commit(); db.close()
    return redirect(url_for("admin_dashboard"))


@app.route("/analytics")
@login_required
@role_required("admin","manager")
def analytics():
    db = get_db()
    region_data = db.execute("""SELECT h.region, ROUND(AVG(r.price),2) avg_price,
                                       SUM(r.total_rooms) total_rooms,
                                       SUM(r.available_rooms) available_rooms
                                FROM hostels h JOIN rooms r ON r.hostel_id=h.id
                                WHERE h.verified=1 GROUP BY h.region ORDER BY avg_price DESC""").fetchall()
    room_data = db.execute("""SELECT room_type, ROUND(AVG(price),2) avg_price,
                                     SUM(total_rooms) total_rooms, SUM(available_rooms) available_rooms
                              FROM rooms GROUP BY room_type ORDER BY avg_price""").fetchall()
    db.close()
    return render_template("analytics.html", region_data=region_data, room_data=room_data)


@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403, message="You do not have permission to view this page."), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="Page not found."), 404


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
else:
    init_db()
