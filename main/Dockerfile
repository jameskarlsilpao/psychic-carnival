# -------------------------
# Stage 1: Python builder
# -------------------------
FROM python:3.13-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

# -------------------------
# Stage 2: Tailwind builder
# -------------------------
FROM node:22-slim AS tailwind-builder

WORKDIR /app

COPY package*.json ./
RUN npm ci || npm install

COPY . .

RUN npm run tailwind


# -------------------------
# Stage 3: Production
# -------------------------
FROM python:3.13-slim

RUN useradd -m -r appuser && \
    mkdir /app && \
    chown -R appuser:appuser /app

COPY --from=builder /usr/local/lib/python3.13/site-packages/ \
    /usr/local/lib/python3.13/site-packages/

COPY --from=builder /usr/local/bin/ \
    /usr/local/bin/

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app/ /app/

# Copy generated Tailwind assets
COPY --from=tailwind-builder /app/static/ /app/static/

# Normalize Windows line endings and make entrypoint executable
RUN sed -i 's/\r$//' /app/entrypoint.prod.sh && \
    chmod +x /app/entrypoint.prod.sh

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

ENTRYPOINT ["/bin/bash", "/app/entrypoint.prod.sh"]
