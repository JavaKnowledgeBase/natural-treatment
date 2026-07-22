FROM python:3.11-slim
WORKDIR /app

COPY shared /app/shared
RUN pip install --no-cache-dir -e /app/shared

COPY seed /app/seed

COPY services/knowledge/botanical/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/knowledge/botanical/main.py .
COPY services/knowledge/botanical/app ./app

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
