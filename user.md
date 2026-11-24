# Kashvo website

Django marketing site + blog CMS. Pages: Home, Why Kashvo, Pricing, About, Blog.

- CMS: `/admin/` (custom). Dashboard, blog posts with CKEditor 5, categories, tags, per-page SEO, redirects, users (super admins only).
- Stock Django admin: `/django-admin/`.
- All settings come from `.env` (python-decouple). See `.env.example` for every key.

## Where things live

| What | Where | In git? |
|---|---|---|
| Code, templates, CSS/JS | `apps/` (Django apps), `config/` (settings, urls), `templates/`, `static/` | Yes |
| The 20 launch articles | `apps/cms/articles/*.html` | Yes |
| Their cover photos | `static/img/blog/<slug>.jpg` | Yes |
| Settings / secrets | `.env` | **No** |
| Database (posts, users, CMS edits) | SQLite `site.sqlite3` locally, MySQL in production | **No** |
| Uploaded files (covers, CKEditor images) | `media/` | **No**, back it up with the database |

`manage.py load_articles` copies the articles into the database and their photos into `media/blog/`.
After that, the database is the source of truth: edit in the CMS. Re-running with `--replace` resets those
20 articles and deletes any other posts.

## Local development

```powershell
copy .env.example .env      # then set DEBUG=True, DB_ENGINE=sqlite, ALLOWED_HOSTS=localhost,127.0.0.1
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py load_articles --replace
.venv\Scripts\python manage.py createsuperuser
.venv\Scripts\python manage.py runserver 8100
```

## Production on CloudPanel

### 1. Create the site and database
1. **Sites → Add Site → Create a Python Site**: domain `kashvo.in`, Python 3.12+, App Port `8090`.
2. **Databases → Add Database**: name `kashvo_site`, user `kashvo_site`, a strong password. CloudPanel's MySQL defaults to `utf8mb4`.
3. **SSL/TLS → New Let's Encrypt Certificate** for `kashvo.in` and `www.kashvo.in`.

### 2. Get the code onto the server (SSH as the site user)
```bash
cd ~/htdocs/kashvo.in
git clone <your-repo-url> repo && cd repo/website
sudo apt install -y pkg-config default-libmysqlclient-dev build-essential python3-dev   # once, as root: needed by mysqlclient
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env      # SECRET_KEY, DB_PASSWORD, hosts
```
Generate a secret key with `python -c "import secrets; print(secrets.token_urlsafe(60))"`.

### 3. Build
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py load_articles --replace     # first deploy only
python manage.py createsuperuser
python manage.py check --deploy
```

### 4. Run with gunicorn (systemd, as root)
`/etc/systemd/system/kashvo-site.service`:
```ini
[Unit]
Description=Kashvo website
After=network.target mysql.service

[Service]
User=kashvo
Group=kashvo
WorkingDirectory=/home/kashvo/htdocs/kashvo.in/repo/website
ExecStart=/home/kashvo/htdocs/kashvo.in/repo/website/.venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8090 --workers 3 --timeout 60
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
systemctl daemon-reload && systemctl enable --now kashvo-site
```
(Replace `kashvo` with your CloudPanel site user.)

### 5. Serve uploaded media from nginx
Static files are served by WhiteNoise. **Media is not** (Django doesn't serve uploads when `DEBUG=False`).
In CloudPanel → the site → **Vhost**, add inside the `server { ... }` block for port 443, above `location /`:
```nginx
location /media/ {
    alias /home/kashvo/htdocs/kashvo.in/repo/website/media/;
    expires 30d;
    access_log off;
}
```

### Updating later
```bash
cd ~/htdocs/kashvo.in/repo && git pull && cd website && . .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate && python manage.py collectstatic --noinput
sudo systemctl restart kashvo-site
```
Don't re-run `load_articles --replace` on updates; it would overwrite CMS edits.

### Back up
The MySQL database (CloudPanel → Databases → Export, or `mysqldump`) **and** the `media/` folder, together.

### Moving existing local content to MySQL
```bash
# on the old (SQLite) setup
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.permission -e sessions -o data.json
# on the new (MySQL) setup, after migrate
python manage.py loaddata data.json
```
and copy the `media/` folder across.
