FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
# This Dockerfile sets up a Python environment, installs dependencies from requirements.txt, and runs a Flask application on port 5000.
# The app.py file is the entry point for the Flask application. You can modify it as per your project structure.