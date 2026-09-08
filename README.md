# انجمن صنفی بهورزان استان مازندران — Behvarzan Site

## Requirements
- Python 3.13
- PostgreSQL 14+ (Production) / SQLite (Development only)

## Installation
\`\`\`powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements/development.txt
\`\`\`

## Environment Variables
کپی از `.env.example` به `.env` و مقداردهی متغیرها.

## Database Setup & Migration
\`\`\`powershell
python manage.py migrate
\`\`\`

## Run Server
\`\`\`powershell
python manage.py runserver
\`\`\`

## Test
\`\`\`powershell
python manage.py test
\`\`\`

## Admin Access
\`\`\`powershell
python manage.py createsuperuser
\`\`\`

## Project Structure
مطابق `apps/` (accounts, organization) و `config/settings/` (base, development, production, test).