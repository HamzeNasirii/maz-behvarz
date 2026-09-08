# راهنمای استقرار (Deployment) — Behvarzan Site

## پیش‌نیاز روی سرور (Ubuntu 22.04+)
```bash
sudo apt update
sudo apt install python3-venv python3-pip postgresql nginx certbot python3-certbot-nginx
```

## ۱. ساخت دیتابیس PostgreSQL
```bash
sudo -u postgres psql
CREATE DATABASE behvarzan_site;
CREATE USER behvarzan_user WITH PASSWORD 'یک-رمز-قوی';
ALTER ROLE behvarzan_user SET client_encoding TO 'utf8';
GRANT ALL PRIVILEGES ON DATABASE behvarzan_site TO behvarzan_user;
\q
```

## ۲. انتقال کد و نصب وابستگی‌ها
```bash
sudo mkdir -p /var/www/behvarzan_site
cd /var/www/behvarzan_site
# کد را از Git یا آپلود دستی این‌جا قرار دهید
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/production.txt
```

## ۳. فایل `.env` واقعی (روی سرور، هرگز در Git)

DJANGO_SECRET_KEY=<کلید قوی تولیدشده در گام ۲۰>
DJANGO_DEBUG=False
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_ALLOWED_HOSTS=behvarzan-mazandaran.ir,www.behvarzan-mazandaran.ir

DATABASE_NAME=behvarzan_site
DATABASE_USER=behvarzan_user
DATABASE_PASSWORD=همون-رمز-بالا
DATABASE_HOST=localhost
DATABASE_PORT=5432

CSRF_TRUSTED_ORIGINS=https://behvarzan-mazandaran.ir


## ۴. Migrate و جمع‌آوری Static Files
```bash
export DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py migrate
python manage.py createcachetable
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## ۵. راه‌اندازی Gunicorn با systemd
```bash
sudo cp deploy/gunicorn.service /etc/systemd/system/behvarzan_site.service
sudo systemctl daemon-reload
sudo systemctl start behvarzan_site
sudo systemctl enable behvarzan_site
```

## ۶. تنظیم Nginx
```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/behvarzan_site
sudo ln -s /etc/nginx/sites-available/behvarzan_site /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## ۷. دریافت گواهی SSL رایگان (Let's Encrypt)
```bash
sudo certbot --nginx -d behvarzan-mazandaran.ir -d www.behvarzan-mazandaran.ir
```

## ۸. بررسی نهایی
```bash
sudo systemctl status behvarzan_site
python manage.py check --deploy --settings=config.settings.production
```

## به‌روزرسانی بعدی (Deploy مجدد)
```bash
cd /var/www/behvarzan_site
git pull
source .venv/bin/activate
pip install -r requirements/production.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart behvarzan_site
```