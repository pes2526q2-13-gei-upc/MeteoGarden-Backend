# MeteoGarden-Backend

We follow a simple and reliable Git workflow to keep the codebase stable and make collaboration easier.

### Branches
- `main`: stable branch (release-ready). No direct pushes.
- `develop`: integration branch. Feature work is merged here via PR.
- `feature/<short-name>`: one branch per task/feature (e.g. `feature/authentication`).
- `fix/<short-name>`: bug fixes.
- `docs/<short-name>`: documentation updates.
- `chore/<short-name>`: maintenance/tooling/dependencies.

### Rules
- No direct pushes to `main` (and ideally none to `develop`).
- All changes go through a Pull Request (PR) into `develop`.
- At least 1 approval before merging.
- PR must pass automated checks (CI) before merging.

### Typical flow
Create a branch from `develop`:
```bash
git checkout develop
git pull
git checkout -b feature/<short-name>
```

Commit and push:
```bash
git add .
git commit -m "feat: <short message>"
git push -u origin feature/<short-name>
```

## Format code for CI/CD pipeline
Install linting dependencies:
```bash
pip install -r cicd-requirements.txt
```

One of the steps of the CI/CD pipeline is the linting & styling step. To format the code to pass this step, you must run the following commands:
```bash
python -m isort .
python -m black .
python -m flake8
```

In order for the pipeline to pass as expected:

All files changed by isort & black must be committed & pushed.
All errors found by flake8 must be solved, committed and pushed. The output of flake8 command should be 0.

Once all of this is done, the pipeline should pass!
## Run the project with Docker
Make sure you have installed:
- Docker 
- Docker Compose

### 1) Create your environment file
Create a `.env` file at the project root.
Copy the .env.example file:
```bash
cp .env.example .env
```

### 2) Build and start the containers
```bash
docker compose up --build
```
This will start:
- `pg`: PostgreSQL database.
- `api`: Django backend.

The API will be available at:
- http://127.0.0.1:8000/

### 3) Apply migrations
In another terminal, run:
```bash
docker compose exec api python manage.py migrate
```

### 4) Test the API
Open in your browser:
- http://127.0.0.1:8000/api/health

Expected response:
```json
{"status":"ok"}
```
### 5) Stop the containers
```bash
docker compose down
```