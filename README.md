# Chip the Alabama Tech Community AI Agent
 
 This project uses uv as its package manager.
 
 ## Installing dependencies
 
 ```bash
 uv sync
 ```
 
 ## Adding a new dependency
 
 ```bash
 uv add <dependency>
 ```
 
 ## Removing a dependency
 
 ```bash
 uv remove <dependency>
 ```
 
 ## Updating a dependency
 
 ```bash
 uv update <dependency>
 ```
 
 ## Exporting the requirements.txt file
 
 ```bash
 uv export --no-hashes -o requirements.txt
 ```
 
 ## Running the debugger
 
 ```bash
 python -m debugpy --listen 5678 --wait-for-client \
 -m hypercorn main:app --reload --log-level debug
 ```
 and to use the launch.json provided in this project.

## Running the app

```bash
hypercorn main:app --reload --log-level debug
```

## Starting the app on Railway

```bash
hypercorn main:app --bind \"[::]:$PORT\"
```

## Running tests

```bash
uv run python -m pytest -q
# or if uv is unavailable
python -m pytest -q
```