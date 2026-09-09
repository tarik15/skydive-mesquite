FROM python:3.11-slim

ARG MONOLITH_UID=1000
ARG MONOLITH_GID=1000

RUN apt-get update && apt-get install -y --no-install-recommends \
        zip \
        mailutils \
        msmtp-mta \
        rename \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g ${MONOLITH_GID} monolith \
 && useradd -u ${MONOLITH_UID} -g monolith -m -s /bin/bash monolith

COPY scripts/zipandmove /usr/bin/zipandmove
COPY scripts/funjumper  /usr/bin/funjumper
RUN chmod +x /usr/bin/zipandmove /usr/bin/funjumper

WORKDIR /home/monolith/webapp

COPY webapp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY webapp/ .
RUN chown -R monolith:monolith /home/monolith/webapp

USER monolith

EXPOSE 5000

CMD ["gunicorn", \
     "--workers", "1", \
     "--bind", "0.0.0.0:5000", \
     "--timeout", "360", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]
