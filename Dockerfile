FROM python:3.14-slim
WORKDIR /service
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt
COPY app app
COPY models models
RUN useradd --create-home service && mkdir -p data && chown -R service:service /service
USER service
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
