FROM python:3.11-slim

COPY pyproject.toml uv.lock README.md /app/

# Install the necessary packages
RUN pip install --upgrade pip uv && \
    uv pip install -r /app/pyproject.toml --system && \
    groupadd -g 55004 pyuser && \
    useradd -u 55005 -g 55004 -d /home/pyadm -m -s /sbin/nologin pyadm

# Copy the current directory contents into the container at /app
COPY . /app

# Set the working directory in the container
WORKDIR /app

USER pyadm

ENV PYTHONPATH="/app/src"

# Run the Python script
ENTRYPOINT ["/usr/local/bin/python3", "src/jp2_remediator/main.py"]
#CMD ["sh", "-c", "cd /app && bash"]

