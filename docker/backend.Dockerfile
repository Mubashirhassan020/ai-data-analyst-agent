FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# WeasyPrint runtime deps (Pango/Cairo/GDK-Pixbuf via GObject) — this is what
# fails with an OSError on a bare Windows dev box; Debian's apt provides it
# directly. libpangocairo-1.0-0 specifically is required alongside libpango
# and libcairo — WeasyPrint's own install docs list it separately.
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
      libcairo2 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY backend/ ./
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
