FROM python:3.12-slim

WORKDIR /code

# Agar production.txt ichida base.txt bor bo'lsa, uni ham nusxalash
COPY requirements/ /code/requirements/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements/production.txt

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
