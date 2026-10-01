FROM python:3.10-slim AS builder
WORKDIR /mind
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.10-slim 
WORKDIR /mind
RUN apt-get update && apt-get install -y git
COPY --from=builder /usr/local /usr/local
COPY . .
CMD ["python","-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
