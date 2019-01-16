FROM ubuntu:18.04

LABEL maintainer="f.rhiem@fz-juelich.de"

# Install required system packages
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y curl python3.7-venv python3.7-distutils && \
    rm -rf /var/lib/apt/lists/*

# Switch to non-root user
RUN useradd -ms /bin/bash sampledb
USER sampledb
WORKDIR /home/sampledb

# Set up Python virtual environment
RUN python3.7 -m venv --without-pip env && \
    curl -sLO https://bootstrap.pypa.io/get-pip.py && \
    env/bin/python get-pip.py && \
    rm get-pip.py

# Install required Python packages
COPY requirements.txt requirements.txt
RUN env/bin/python -m pip install -r requirements.txt

# Copy sampledb source code
ADD sampledb sampledb

# By default, expect a normal postgres container to be linked
ENV SAMPLEDB_SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://postgres:@postgres:5432/postgres"

# By default, run the sampledb server
ENTRYPOINT ["env/bin/python", "-m", "sampledb"]
CMD ["run"]

HEALTHCHECK --interval=1m --timeout=3s --start-period=1m CMD curl -f -H "Host: $SAMPLEDB_SERVER_NAME" "http://localhost:8000$SAMPLEDB_SERVER_PATH/status/" || exit 1
