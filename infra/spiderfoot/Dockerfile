# SpiderFoot v4.0's upstream Alpine/Python 3.8 image cannot build PyYAML 5.4.1
# reliably on Apple Silicon. Use a current Debian Python image and retain the
# upstream application source at its v4.0 release tag.
FROM python:3.11-slim

ARG SPIDERFOOT_REF=v4.0

RUN apt-get update \
    && apt-get install --no-install-recommends -y gcc git libffi-dev libjpeg-dev libxml2-dev libxslt1-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone --depth 1 --branch "${SPIDERFOOT_REF}" https://github.com/smicallef/spiderfoot.git

WORKDIR /opt/spiderfoot
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && sed -i 's/pyyaml>=5.4.1,<6/PyYAML>=6,<7/I' requirements.txt \
    && python -m pip install --no-cache-dir -r requirements.txt

ENV SPIDERFOOT_DATA=/var/lib/spiderfoot \
    SPIDERFOOT_LOGS=/var/lib/spiderfoot/log \
    SPIDERFOOT_CACHE=/var/lib/spiderfoot/cache
RUN useradd --create-home --shell /usr/sbin/nologin spiderfoot \
    && mkdir -p "$SPIDERFOOT_DATA" "$SPIDERFOOT_LOGS" "$SPIDERFOOT_CACHE" \
    && chown -R spiderfoot:spiderfoot "$SPIDERFOOT_DATA"

USER spiderfoot
EXPOSE 5001
CMD ["python", "sf.py", "-l", "0.0.0.0:5001"]
