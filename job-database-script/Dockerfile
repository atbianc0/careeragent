FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set PYTHONPATH to include the root directory so backend modules can be resolved
ENV PYTHONPATH=/app

CMD ["tail", "-f", "/dev/null"]
