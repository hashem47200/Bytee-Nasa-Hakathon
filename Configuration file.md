# \# ==========================================

# \# 1. ONE-CLICK LAUNCH (Windows Executable)

# \# ==========================================

# Double-click `Start-NASA-Explorer-Hub.exe` (or `Start-NASA-Explorer-Hub.bat`) to automatically set up and start the server.

# Open http://127.0.0.1:8123 in your browser.

# 

# \# ==========================================

# \# 2. MANUAL LOCAL SERVER SETUP

# \# ==========================================

# \# Windows (PowerShell / CMD)

# python -m pip install -r requirements.txt

# python manage.py migrate

# python manage.py import\_missions

# python manage.py runserver 127.0.0.1:8123

# 

# \# Linux / macOS

# chmod +x start.sh

# ./start.sh

# 

# \# Local Access \& Admin

# Local URL:   http://127.0.0.1:8123

# Admin URL:   http://127.0.0.1:8123/admin/

# Credentials: admin / admin123

# 

# \# ==========================================

# \# 3. PRODUCTION DEPLOYMENT

# \# ==========================================

# \# Environment Variables (.env)

# DJANGO\_SECRET\_KEY=<your-secure-random-string>

# DJANGO\_DEBUG=False

# DJANGO\_ALLOWED\_HOSTS=nasa-explorer.yourdomain.com

# 

# \# Static Files \& Gunicorn Server

# python manage.py collectstatic --noinput

# gunicorn nasa\_hub.wsgi:application --bind 0.0.0.0:8000 --workers 3

# 

# \# ==========================================

# \# 4. VERIFICATION \& TESTS

# \# ==========================================

# python manage.py test

