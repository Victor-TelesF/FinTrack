FROM python:3.13-slim

WORKDIR /app

# Instala dependências essenciais do sistema para compilar pacotes se necessário
RUN apt-get update && apt-get install -y git libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Comando para iniciar o Uvicorn apontando para o seu arquivo main.py
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]