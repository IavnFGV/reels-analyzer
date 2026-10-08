# Recording Checklist

## Prepare

```bash
bash docs/devcontainer-context-mystery/create-demo-payload.sh 512
```

Use `1024` if you want a more dramatic pause.

## Broken demo

Working directory:

[broken](/opt/projects/reels-analyzer/docs/devcontainer-context-mystery/broken)

Steps:

1. Open the folder in VS Code
2. Run `Dev Containers: Rebuild and Reopen in Container`
3. Wait for the pause after preflight
4. Run:

```bash
docker build -f .devcontainer/Dockerfile . --progress=plain
```

5. Capture `load build context`
6. Capture `transferring context: ...MB`

## Fixed demo

Working directory:

[fixed](/opt/projects/reels-analyzer/docs/devcontainer-context-mystery/fixed)

Steps:

1. Open the folder in VS Code
2. Show [.dockerignore](/opt/projects/reels-analyzer/docs/devcontainer-context-mystery/fixed/.dockerignore)
3. Run `Dev Containers: Rebuild and Reopen in Container`
4. Run:

```bash
docker build -f .devcontainer/Dockerfile . --progress=plain
```

5. Capture `transferring context: 378B` or similarly tiny output
6. Capture `payload missing`

## Optional shots

- Show [README.md](/opt/projects/reels-analyzer/docs/devcontainer-context-mystery/README.md)
- Show [broken/.devcontainer/devcontainer.json](/opt/projects/reels-analyzer/docs/devcontainer-context-mystery/broken/.devcontainer/devcontainer.json)
- Show [fixed/.dockerignore](/opt/projects/reels-analyzer/docs/devcontainer-context-mystery/fixed/.dockerignore)
