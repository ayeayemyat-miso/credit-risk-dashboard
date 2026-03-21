# Use Python 3.12 as the base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port Render expects
EXPOSE 10000

# Run the application with gunicorn
CMD ["gunicorn", "app.dashboard:server", "--bind", "0.0.0.0:10000"]