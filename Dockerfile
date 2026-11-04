FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential default-libmysqlclient-dev pkg-config && rm -rf /var/lib/apt/lists/*
ARG ENABLE_ALIYUN_SMS=false
COPY requirements*.txt ./
RUN if [ "$ENABLE_ALIYUN_SMS" = "true" ]; then pip install --no-cache-dir -r requirements-sms.txt gunicorn==23.0.0; else pip install --no-cache-dir -r requirements.txt gunicorn==23.0.0; fi
COPY . .
RUN useradd --uid 10001 --create-home shop && mkdir -p /app/staticfiles && chown shop:shop /app/staticfiles
USER shop
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-"]
