FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY Accordance /app

RUN addgroup --system accordance \
    && adduser --system --ingroup accordance --home /nonexistent --no-create-home accordance \
    && mkdir -p /data/web_clients \
    && chown -R accordance:accordance /app /data

USER accordance

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"]

CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
