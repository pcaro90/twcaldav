FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install TaskWarrior and dependencies
RUN apt-get update && apt-get install -y \
    taskwarrior \
    python3.11 \
    python3-pip \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Create taskwarrior data directory
RUN mkdir -p /taskdata
ENV TASKDATA=/taskdata

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies
RUN uv sync

# Initialize taskwarrior
RUN task rc.confirmation=off rc.data.location=/taskdata version

CMD ["/bin/bash"]
