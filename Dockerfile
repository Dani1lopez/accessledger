FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8080

RUN sed -i 's/\r//' entrypoint.sh

CMD ["sh", "./entrypoint.sh"]