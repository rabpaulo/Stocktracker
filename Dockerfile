FROM python:3.13-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TERM=xterm-256color

WORKDIR /app

RUN addgroup --system stocktracker \
    && adduser --system --ingroup stocktracker --home /home/stocktracker stocktracker

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY --chown=stocktracker:stocktracker main.py ./
COPY --chown=stocktracker:stocktracker config/config.json ./config/config.json

USER stocktracker

ENTRYPOINT ["python", "main.py"]
