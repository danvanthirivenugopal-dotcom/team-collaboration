FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for OpenCV and Streamlit
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirement files and install
COPY requirements.txt requirements_backend.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements_backend.txt

# Copy the rest of the application code
COPY . .

# Ensure upload directories exist
RUN mkdir -p uploads/users uploads/admins uploads/registered uploads/attendance_logs uploads/enrollments

# Make the startup script executable
RUN chmod +x start.sh

# Run the unified startup script
CMD ["./start.sh"]
