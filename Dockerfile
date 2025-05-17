FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

EXPOSE 8000

CMD ["uvicorn", "dashboard_server:app", "--host", "0.0.0.0", "--port", "8000"] 