# Devcontainer Context Mystery

This demo reproduces the "initializeCommand passed, then silence" effect caused by a huge Docker build context.

Folders:

- `broken/`: intentionally missing `.dockerignore`
- `fixed/`: same setup, but excludes the heavy payload from the build context

How to use:

1. Run `bash docs/devcontainer-context-mystery/create-demo-payload.sh`
2. In VS Code, open either `docs/devcontainer-context-mystery/broken` or `docs/devcontainer-context-mystery/fixed`
3. Run `Dev Containers: Rebuild and Reopen in Container`

What to expect:

- `broken/`: after `initializeCommand`, Dev Containers may appear stuck while Docker archives and transfers the payload directory
- `fixed/`: build proceeds immediately because `.dockerignore` removes the payload from the context

Useful terminal check:

```bash
docker build -f .devcontainer/Dockerfile . --progress=plain
```

In the bad case you should see a large `transferring context:` value.
In the fixed case it should be tiny.
