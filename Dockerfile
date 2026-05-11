# ── Stage 1: Build React frontend ────────────────────────────────────
FROM node:20-alpine AS frontend

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

COPY . .
RUN npm run build


# ── Stage 2: Python backend + static assets ─────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY main.py .
COPY run.py .
COPY backend ./backend

# Copy built frontend from Stage 1
COPY --from=frontend /app/dist ./dist

# Expose the port Zeabur expects
EXPOSE 8080

# Start FastAPI server via bootstrap script
CMD ["python", "run.py"]
