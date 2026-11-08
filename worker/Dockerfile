# Use the CPU runtime that was verified locally, without copying model weights.
FROM ubuntu:24.04
USER root
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 libgomp1 libstdc++6 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY worker/runtime/ /opt/sd/
RUN chmod +x /opt/sd/sd-cli
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 LD_LIBRARY_PATH=/opt/sd
WORKDIR /app
COPY worker/*.py /app/worker/
COPY worker/model-presets.json /app/worker/model-presets.json
COPY setupkit/ /app/setupkit/
ENTRYPOINT ["python3", "-m", "worker.runner"]
