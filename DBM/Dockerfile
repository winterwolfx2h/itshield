# Use the official Python image
FROM python:3.12-slim

# Set the working directory in the container
#WORKDIR /app

# Copy the application files
#COPY . /app

# Install dependencies
#RUN pip install --no-cache-dir -r requirements.txt

# Expose the application port
#EXPOSE 5000

# Run the application
#CMD ["python", "app.py"]


#FROM python:3.9-slim

WORKDIR /app

COPY DBM/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY DBM/ .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]