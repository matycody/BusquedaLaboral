FROM python:3.12-slim
WORKDIR /app
COPY . .
ENV BL_PUBLIC=1 PYTHONUNBUFFERED=1
VOLUME /app/data
EXPOSE 8000
CMD ["python", "run.py", "8000"]
