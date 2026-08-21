# =========================
# Stage 1: Python dependencies
# =========================
FROM python:3.13-slim AS python-builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =========================
# Stage 2: Tailwind builder
# =========================
FROM node:22-slim AS tailwind-builder

WORKDIR /app

COPY package*.json .
RUN npm ci

# Copy Tailwind source AND the templates it needs to scan
COPY portfolio/static/src ./portfolio/static/src
COPY portfolio/templates ./portfolio/templates

RUN npm run tailwind

# =========================
# Stage 3: Production
# =========================
FROM python:3.13-slim

RUN useradd -m -r appuser && \
    mkdir /app && \
    chown -R appuser:appuser /app

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Python dependencies
COPY --from=python-builder /usr/local/lib/python3.13/site-packages/ \
    /usr/local/lib/python3.13/site-packages/

COPY --from=python-builder /usr/local/bin/ \
    /usr/local/bin/

# Django project
COPY --chown=appuser:appuser . .

# Compiled Tailwind CSS
COPY --from=tailwind-builder \
    /app/portfolio/static/src/output.css \
    /app/portfolio/static/src/output.css

# Entrypoint
RUN sed -i 's/\r$//' /app/entrypoint.prod.sh && \
    chmod +x /app/entrypoint.prod.sh

USER appuser

EXPOSE 8000

ENTRYPOINT ["/bin/bash", "/app/entrypoint.prod.sh"]