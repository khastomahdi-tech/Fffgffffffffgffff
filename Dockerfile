FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --timeout=100

COPY bot.py .

CMD ["python", "bot.py"]
