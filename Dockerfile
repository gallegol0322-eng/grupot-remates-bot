# ---- Usar Python 3.10 (slim para tamaño pequeño) ----
FROM python:3.10-slim

# ---- Crear directorio de trabajo ----
WORKDIR /app

# ---- Instalar dependencias del sistema necesarias para Torch / SciPy ----
RUN apt-get update && \
    apt-get install -y build-essential gcc g++ git && \
    apt-get clean

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
