# Broken Demo

This folder intentionally has no `.dockerignore`.

If `payload/` is large, Docker will archive and transfer it during `load build context`, and `COPY . ./` will bring that payload into the image.
