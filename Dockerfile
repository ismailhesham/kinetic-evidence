FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg espeak-ng fonts-dejavu-core git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p outputs workspaces assets/media assets/geo assets/fonts

EXPOSE 7860
CMD ["python3", "app.py"]