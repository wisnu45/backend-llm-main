FROM python:3.10.13

# Install dependencies
RUN apt-get update \
  && apt-get -y install --no-install-recommends \
     poppler-utils tesseract-ocr libtesseract-dev \
     libgl1-mesa-glx libglib2.0-0 libnss3 libxss1 libasound2 \
     libatk1.0-0 libatk-bridge2.0-0 libcups2 libx11-6 libxcomposite1 \
     libxcursor1 libxdamage1 libxrandr2 libxinerama1 libgbm1 \
     libpango-1.0-0 libpangocairo-1.0-0 libgtk-3-0 \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Copy application files
COPY . /combiphar-be

# Create and change to the app directory.
WORKDIR /combiphar-be
COPY env.example .env

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/combiphar-be

RUN chmod 444 app/server.py
RUN chmod 444 requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

#  Install Playwright browser with dependencies
RUN playwright install --with-deps

# Create necessary directories
RUN mkdir -p data/documents/portal data/documents/admin data/documents/user logs
RUN chmod 775 data
RUN chmod 775 logs

# Service must listen to $PORT environment variable.
ENV PORT=8070

# Start the application directly
CMD ["python3", "app/server.py"]
