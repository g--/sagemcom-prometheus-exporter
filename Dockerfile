FROM python:3.10-alpine

EXPOSE 8000
ENV SAGEMCOM_HOST= \
 SAGEMCOM_USERNAME=admin \
 SAGEMCOM_PASSWORD= \
 SAGEMCOM_POLL_INTERVAL_SECONDS=10

COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY main.py .
CMD ["python", "main.py"]



