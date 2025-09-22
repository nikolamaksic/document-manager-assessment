# Propylon Document Manager Assessment

The Propylon Document Management Technical Assessment is a simple (and incomplete) web application consisting of a basic API backend and a React based client.  This API/client can be used as a bootstrap to implement the specific features requested in the assessment description. 

## Getting Started
### API Development
The API project is a [Django/DRF](https://www.django-rest-framework.org/) project that utilizes a [Makefile](https://www.gnu.org/software/make/manual/make.html) for a convenient interface to access development utilities. This application uses [SQLite](https://www.sqlite.org/index.html) as the default persistence database you are more than welcome to change this. This project requires Python 3.11 in order to create the virtual environment.  You will need to ensure that this version of Python is installed on your OS before building the virtual environment.  Running the below commmands should get the development environment running using the Django development server.
1. `$ make build` to create the virtual environment.
2. `$ make fixtures` to create a small number of fixture file versions.
3. `$ make serve` to start the development server on port 8001.
4. `$ make test` to run the limited test suite via PyTest.
### Client Development 
See the Readme [here](https://github.com/propylon/document-manager-assessment/blob/main/client/doc-manager/README.md)

##
[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)

## API Endpoints

All endpoints require **Token authentication** (`Authorization: Token <your_token>`)
unless otherwise noted.

### 📄 Document Management

| Method | Path | Description | Request Body | Notes |
|-------|------|-------------|--------------|------|
| **GET** | `/documents/{path}` | Retrieve a file. Returns the latest version by default or a specific revision if `?revision=<int>` is provided. | – | `{path}` is the logical document path (e.g. `documents/review.pdf`). |
| **POST** | `/documents/{path}` | Upload a new version of the file. | `file` (multipart/form-data) | Creates or updates a `FileVersion`. |
| **DELETE** | `/documents/{path}` | Delete a version of the file. Deletes the latest version if no `revision` is provided. | – | If all versions are removed, the underlying `BaseFile` is also deleted. |
| **GET** | `/documents/diff/{path}` | HTML side-by-side diff between two revisions of a UTF-8 text file. | – | Query params: `from=<int>&to=<int>`. Returns raw HTML for browser display. |
| **GET** | `/documents/mine` | List **all** documents belonging to the authenticated user, including all versions. | – | Useful for dashboards or file pickers. |
### 👤 User Management

| Method | Path | Description | Request Body | Notes |
|-------|------|-------------|--------------|------|
| **POST** | `/user/create/` | Create a new user account. | `username`, `email`, `password` | Open to unauthenticated clients. |
| **POST** | `/user/token/` | Obtain an auth token for an existing user. | `username`, `password` | Use this token for all authenticated requests. |
| **GET / PUT / PATCH** | `/user/profile/` | Retrieve or update the authenticated user’s profile. | Optional: `username`, `email`, `password` | Requires authentication. |

### 🔑 Authentication

| Method | Path | Description | Request Body |
|-------|------|-------------|--------------|
| **POST** | `/auth-token/` | Obtain an authentication token (alternative endpoint to `/user/token/`). | `username`, `password` |

### 📜 Schema & Interactive API Docs

| Method | Path | Description |
|-------|------|-------------|
| **GET** | `/api/schema/` | Machine-readable OpenAPI schema for the full API. |
| **GET** | `/api/docs/` | Interactive Swagger-UI documentation (browse & test endpoints). |
| **GET** | `/api-auth/login/`, `/api-auth/logout/` | DRF browsable API login/logout (for development). |

---

### Example Usage

**Upload a new version**

```bash
curl -X POST \
     -H "Authorization: Token <TOKEN>" \
     -F "file=@/path/to/local/review.pdf" \
     http://127.0.0.1:8000/api/documents/documents/review.pdf
