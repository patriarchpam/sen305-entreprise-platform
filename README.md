# VUA ServiceDesk (SEN305 Service Platform)

An enterprise service request platform for reporting and tracking
maintenance requests. Built week by week as the SEN305 practical project.

## Structure

```
backend/          Django project (config) and core app
frontend/         Frontend (later)
docs/             Documentation
infrastructure/   Deployment and configuration (later)
```

## Run the backend (Windows)

```cmd
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/ (home) and http://127.0.0.1:8000/about/.

Create an admin login with `python manage.py createsuperuser`,
then visit http://127.0.0.1:8000/admin/.

## Pages

| URL | Description |
|---|---|
| `/` | Home with platform status |
| `/about/` | Project overview and system roles |
| `/admin/` | Django admin |
