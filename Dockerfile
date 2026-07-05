# Production container for AI-Driven BDD Pipeline with Formal Verification
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system utilities, python, and sqlite3
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    unzip \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Download and install verified Dafny v4.2.0 compiler release
RUN curl -L -o dafny.zip https://github.com/dafny-lang/dafny/releases/download/v4.2.0/dafny-4.2.0-x64-ubuntu-20.04.zip \
    && unzip dafny.zip -d /opt/ \
    && rm dafny.zip
ENV PATH="/opt/dafny:${PATH}"

WORKDIR /app

# Install python requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy codebase
COPY . .

# Configure default database targets
ENV SPANNER_DATABASE=bdd-db

EXPOSE 8080

CMD ["python3", "run_eval.py"]
