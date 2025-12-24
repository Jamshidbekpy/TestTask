#!/bin/bash

# PostgreSQL databaza tayyor bo'lishini kutish (netcatsiz versiya)
echo "PostgreSQL ni kutish..."
counter=0
max_attempts=30

# Python yordamida connection tekshirish
until python -c "
import socket
import sys
try:
    sock = socket.create_connection(('postgres_db', 5432), timeout=2)
    sock.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    sleep 1
    counter=$((counter + 1))
    if [ $counter -ge $max_attempts ]; then
        echo "PostgreSQL ulanishi muvaffaqiyatsiz! $max_attempts urinishdan so'ng."
        exit 1
    fi
    echo "Kutish ($counter/$max_attempts)..."
done

echo "PostgreSQL ishga tushdi!"

# Migrationslarni yaratish
echo "Migrations yaratilmoqda..."
python manage.py makemigrations

# Migratelarni amalga oshirish
echo "Migratelar amalga oshirilmoqda..."
python manage.py migrate

# Superuser yaratish (agar mavjud bo'lmasa)
echo "Superuser tekshirilmoqda..."
python manage.py shell << EOF
import os
from django.contrib.auth import get_user_model
User = get_user_model()

SUPERUSER_EMAIL = os.environ.get('DJANGO_SUPERUSER_EMAIL')
SUPERUSER_PASSWORD = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

if SUPERUSER_EMAIL and SUPERUSER_PASSWORD:
    if not User.objects.filter(email=SUPERUSER_EMAIL).exists():
        User.objects.create_superuser(
            email=SUPERUSER_EMAIL,
            password=SUPERUSER_PASSWORD
        )
        print(f"Superuser {SUPERUSER_EMAIL} yaratildi!")
    else:
        print(f"Superuser {SUPERUSER_EMAIL} allaqachon mavjud!")
else:
    print("Superuser ma'lumotlari .env faylida to'liq emas!")
EOF

# Buyruqni ishga tushirish
exec "$@"