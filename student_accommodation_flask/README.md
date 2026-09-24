# HostelConnect — Booking Made Simple

A school-project-ready Flask + SQLite prototype for a Ghana-wide student accommodation platform.

## What is included

### Student
- Register/login
- Search hostels by region and university
- See currently available rooms near the selected campus
- View prices, rooms, facilities and locations
- See available/unavailable rooms
- Save/favorite accommodation
- Reserve a room through a clearly marked **demo payment flow**
- Report outdated information
- View booking history

### Landlord / Agent
- Register/login
- Add accommodation
- Add room types and prices
- Set total and available rooms
- Update room price/availability
- View transactions and student/institution details for their properties

### Administrator
- Approve accommodation listings
- Remove listings
- Monitor reports
- View users/listings/verification statistics
- View transaction volume
- Access rental-price and availability analytics

## Run locally

1. Install Python 3.10+.
2. Open a terminal in this project folder.
3. Create a virtual environment:

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Start the application:

```bash
python app.py
```

6. Open:
`http://127.0.0.1:5000`

The SQLite database is created automatically at `instance/accommodation.db`.

## Demo accounts

- Admin: `admin@hostelconnect.local` / `admin123`
- Manager: `manager@hostelconnect.local` / `manager123`
- Student: `student@hostelconnect.local` / `student123`

Change all demo passwords and the Flask secret key before any real deployment.

## Important production upgrades

This is intentionally a prototype. Before turning it into the Ghana-wide production platform, add:

- Real payment gateway integration (e.g. a Ghana-supported provider)
- HTTPS and secure secret management
- CSRF protection
- Strong password and account verification flows
- Email/SMS/WhatsApp notifications
- Image upload storage (cloud object storage)
- Real maps/geocoding
- Manager/agent identity and business verification
- More granular permissions
- Audit logs
- Rate limiting and security monitoring
- PostgreSQL for production scale
- Background jobs
- Automated backups
- Privacy policy, terms, consent and data-retention controls
- Proper tenancy/booking lifecycle (pending, confirmed, checked-in, checked-out, cancelled)
- Subscription/slot billing for hostel owners
- Advertising management for nearby vendors
- Python analytics service using pandas/numpy/scikit-learn
- Mobile app using Flutter or React Native against the same API

## Architecture direction

For the academic prototype:
Browser -> Flask -> SQLite

For the future Ghana-wide system:
Web/Mobile -> Flask/FastAPI API -> PostgreSQL
                         |
                         -> Analytics service (pandas/numpy/scikit-learn)
                         -> Payment provider
                         -> Maps/geocoding
                         -> Notifications
                         -> Image/object storage
