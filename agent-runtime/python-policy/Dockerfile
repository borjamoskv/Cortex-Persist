FROM python:3.11-slim

WORKDIR /app

# Install grpc build dependencies
RUN apt-get update && apt-get install -y build-essential

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# We need the proto files to compile them
COPY . .
# Let's assume proto/ is mounted or copied in standard setup, 
# for docker we copy proto at the docker-compose level but dockerfile context is just python-policy
# For simplicity, we just run the server.

CMD ["python", "server.py"]
