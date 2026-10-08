# Fixed Demo

This folder adds `.dockerignore`, so `payload/` does not enter the Docker build context.

The Dockerfile is the same as in `broken/`, but `load build context` stays small and `payload/` never reaches the image.
