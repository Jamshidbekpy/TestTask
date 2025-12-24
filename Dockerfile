FROM python:3.12-slim

WORKDIR /code

# System dependencies - netcat-traditional debian package
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Agar production.txt ichida base.txt bor bo'lsa, uni ham nusxalash
COPY requirements/ /code/requirements/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements/production.txt

# Entrypoint faylini nusxalash va ruxsat berish
COPY docker-entrypoint.sh /code/docker-entrypoint.sh
RUN chmod +x /code/docker-entrypoint.sh

# Keyin qolgan fayllarni nusxalash
COPY . .

ENTRYPOINT ["/code/docker-entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]