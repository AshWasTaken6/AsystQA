FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend

WORKDIR /app

RUN addgroup --system asystqa && adduser --system --ingroup asystqa asystqa

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend /app/backend

RUN mkdir -p /app/backend/memory /app/backend/audit && chown -R asystqa:asystqa /app

USER asystqa

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend"]
