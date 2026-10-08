FROM mcr.microsoft.com/devcontainers/python:3-bookworm

WORKDIR /workspace/context-mystery

COPY . ./

RUN python -V \
    && if [ -f payload/demo.bin ]; then ls -lh payload/demo.bin; else echo "payload missing"; fi
