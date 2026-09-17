FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN sed -i 's/\r//' entrypoint.sh && chmod +x entrypoint.sh

# Dedicated non-root runtime user; only the runtime-writable directory
# (/app/staticfiles) is granted to it — never the whole /app tree.
RUN groupadd --system app && useradd --system --gid app --create-home app \
    && mkdir -p /app/staticfiles \
    && chown -R app:app /app/staticfiles

USER app

EXPOSE 8080

CMD ["sh", "./entrypoint.sh"]
