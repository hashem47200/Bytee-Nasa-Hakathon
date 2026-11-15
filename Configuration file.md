# \# ==========================================

# \# 1. MANUAL LOCAL SERVER SETUP

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

# \# 2. PRODUCTION DEPLOYMENT

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

# \# 3. VERIFICATION \& TESTS

# \# ==========================================

# python manage.py test

