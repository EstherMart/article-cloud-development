
FROM python:3.12-slim

# Diretório de trabalho
WORKDIR /app

# Evita arquivos .pyc e mantém logs visíveis
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código
COPY . .

# Porta do Django
EXPOSE 8000

# Inicialização
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
