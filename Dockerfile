# Start with Official Python Base
# We also need Java + Maven for the Agent to perform its job
FROM python:3.11-slim

# 1. Install System Dependencies (Java 17, Maven)
# This implements our "Sustainable Validation" architecture
RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    maven \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Environment
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

# 2. Setup Python Environment
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. WARM BAKING STRATEGY (The "Optimization")
# Copy the template POM first
COPY backend/config/warmup_pom.xml /tmp/warmup_pom.xml

# Run Maven "Go Offline" to download the internet
# This creates a cached layer with all our heavy JARs
RUN echo "Downloading Maven dependencies..." && \
    mvn -f /tmp/warmup_pom.xml dependency:go-offline && \
    mvn -f /tmp/warmup_pom.xml dependency:resolve-plugins && \
    rm /tmp/warmup_pom.xml

# 4. Copy Application Code
# Note: We copy this AFTER the heavy Maven layer so code changes don't bust the cache
COPY backend ./backend
COPY frontend ./frontend

# 5. Runtime Config
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose Port
EXPOSE 8000

# Start Command
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
