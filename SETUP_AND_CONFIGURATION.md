# NASA Explorer Hub · Architecture & Deployment Guide

## 1. Overview
The **NASA Explorer Hub** is a multi-page web platform and aerospace educational portal. It categorizes missions across Mars, the Moon, and Deep Space, allowing users to explore missions, launch dedicated mission exams, score against a strict 60% passing threshold, and earn verifiable, personalized NASA Explorer Certificates.

---

## 2. Core Architectural Components

### A. Dedicated Quiz & Exam Route (`/vehicle/<slug>/quiz/`)
- **Step-by-Step Card Flow:** Renders dynamic questions pulled from the database in an interactive card layout with keyboard shortcuts (1–4) and progress tracking.
- **60% Passing Threshold:**
  - **Score < 60%:** Displays a telemetry failure alert (`⚠ TELEMETRY LOST`) with detailed answer review and a prominent `🔄 Retake Exam` CTA.
  - **Score >= 60%:** Displays the `🏅 MISSION SUCCESS` achievement badge and unlocks the personalized NASA Explorer Certificate.
- **Dynamic Database Extensibility:** Administrators can add, reorder, or update questions and multiple-choice options anytime from the Django admin.

### B. Full Admin Dashboard (`/admin/`)
- Accessible at `/admin/`.
- Superuser credentials:
  - **Username:** `admin`
  - **Password:** `admin123`
- **Inline Question & Narrative Editing:** Vehicles feature `QuestionInline`, `StoryInline`, and `VehicleSpecInline` allowing administrators to manage the complete mission dossier from a single screen.

### C. UI/UX Color Contrast & Dark Mode Aesthetic
- **Mission Control Theme:** Built on a deep cosmic palette (`#04070f`, `#0a1226`) with sharp, high-contrast typography (`#ffffff` and `#e6eefc` light-gray tones, meeting WCAG AAA >= 9:1 contrast).
- **Accents:** Neon cyan (`#38e1ff`), emerald green (`#3dff9a`), amber (`#ffc94d`), and cosmic violet (`#b9a2ff`) with glowing status badges and pulsating CTA buttons.

### D. Space Category Relocation (Deep Space Framing)
- Deep-space probes and observatories (*James Webb Space Telescope*, *Voyager 1*, *Parker Solar Probe*, *Kepler*, *Pioneer 10*, *Dawn*, *NEAR Shoemaker*) are isolated in a planet-free cosmic framing without surface terrain or landing contexts.

### E. Multi-Page Architecture & Clean URLs
1. **Home / Hub (`/`)**: Toggle bar for **Mars**, **Moon**, and **Space** with instant client-side filtering and real-time crew certification trackers.
2. **Vehicle Story Page (`/vehicle/<slug>/`)**: Editorial layout with technical specifications, mission log narrative, and prominent `Launch Mission Exam 🚀` CTA.
3. **Dedicated Exam Page (`/vehicle/<slug>/quiz/`)**: Step-by-step 60% threshold evaluation interface.
4. **Certificate Page (`/certificate/`)**: Personal credential gallery and vector PDF download (`/certificate/<code>/download/`).

---

## 3. Quick Start & Local Run

### Windows
Double-click `Start-NASA-Explorer-Hub.bat` or run:
```powershell
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py import_missions
python manage.py runserver 127.0.0.1:8123
```
Open [http://127.0.0.1:8123](http://127.0.0.1:8123) in your browser.

### Linux / macOS
```bash
chmod +x start.sh
./start.sh
```

---

## 4. Production Deployment

1. **Environment Variables:**
   - `DJANGO_SECRET_KEY`: Set a secure random string.
   - `DJANGO_DEBUG`: Set to `False`.
   - `DJANGO_ALLOWED_HOSTS`: Comma-separated domain names (e.g., `nasa-explorer.yourdomain.com`).

2. **Static Assets:**
   Static files are collected and served via WhiteNoise with compression and caching:
   ```bash
   python manage.py collectstatic --noinput
   ```

3. **Production Server:**
   Run using Gunicorn:
   ```bash
   gunicorn nasa_hub.wsgi:application --bind 0.0.0.0:8000 --workers 3
   ```

---

## 5. Verification & Tests
Run the automated test suite:
```bash
python manage.py test
```
All unit tests verify:
- Category distinction (Planetary vs Deep Space)
- Database extensibility (2 questions per vehicle)
- 60% threshold failure & success logic
- Personalized Certificate creation & vector PDF rendering
- Clean routing and admin inlines
