# ---- Usar Python 3.10 ----
FROM python:3.10-slim

# ---- Crear directorio de trabajo ----
WORKDIR /app

# ---- Copiar requirements ----
COPY requirements.txt .

# ---- Instalar dependencias ----
RUN pip install --no-cache-dir -r requirements.txt

# ---- Copiar el resto del código ----
COPY . .

# ---- Render usa el puerto 10000 ----
ENV PORT=10000

# ---- Comando para iniciar la app ----
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:10000"]
