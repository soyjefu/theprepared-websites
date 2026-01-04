# WordPress to Django Migration Plan

## 1. Project Goal
Migrate the existing **WordPress** blog to a custom **Django** application while maintaining:
1.  **URL Structure**: Keep the same domain and permalinks to preserve SEO.
2.  **Data**: Migrate all posts, categories, tags, and media from MariaDB (MySQL) to PostgreSQL.
3.  **Design**: Replicate the current WordPress theme's look and feel using Django Templates and CSS.
4.  **Infrastructure**: Integrate into the existing Docker ecosystem (`theprepared`), utilizing the shared PostgreSQL database.

## 2. Directory Structure Plan
Current:
```
websites/
└── wordpress-app/ (To be Deprecated)
```

New:
```
websites/
├── django_blog/       # New Django Project Root
│   ├── manage.py
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config/        # Project Settings (Core)
│   ├── blog/          # Main Blog App
│   │   ├── models.py  # Post, Category, Tag models
│   │   ├── views.py
│   │   └── templates/
│   ├── theme/         # Static files & Global Templates
│   └── migration_tools/ # Scripts for data import
```

## 3. Detailed Workflow

### Phase 1: Setup Django Environment
1.  **Initialize Project**: Create a new Django project `django_blog` inside `websites/`.
2.  **Database Connection**: Configure `settings.py` to connect to the shared `postgres_db` container.
3.  **Model Design**: Create Django models that mirror WordPress core tables but optimized for Django.
    *   `Post`: title, content (HTML), slug, published_date, author, status.
    *   `Category` & `Tag`: For classification.
    *   `Media`: For managing uploaded images.

### Phase 2: Design Porting (Theme)
1.  **Analyze Current Theme**: Inspect the running WordPress site to extract:
    *   Main layout (Header, Footer, Sidebar).
    *   CSS styles (fonts, colors, spacing).
    *   JavaScript assets.
2.  **Template Creation**:
    *   `base.html`: The skeleton template including header/footer/css.
    *   `post_list.html`: For the main page and archives.
    *   `post_detail.html`: For individual articles.
3.  **Static Files**: Move extracted CSS/JS/Images to `django_blog/static/`.

### Phase 3: Data Migration (The Hard Part)
*Objective: Move data from MariaDB (WP) to PostgreSQL (Django).*

1.  **Export Data**: Use `mysqldump` or a SQL query to export `wp_posts`, `wp_terms`, `wp_term_relationships` to JSON/CSV.
2.  **Migration Script**: Write a Python management command (`python manage.py import_wordpress`) to:
    *   Read the exported JSON.
    *   Clean up content (e.g., adjust image paths from `/wp-content/uploads/...` to `/media/...`).
    *   Create `Post` objects in Django/Postgres.
    *   Handle many-to-many relationships (Tags/Categories).
3.  **Media Files**: Copy physical files from the WordPress volume to the new Django media volume.

### Phase 4: Infrastructure & Switchover
1.  **Dockerize**: Create `Dockerfile` for the Django app using `gunicorn`.
2.  **Update Compose**: Modify `websites/docker-compose.yml`:
    *   Comment out/remove the `wordpress` service.
    *   Add the new `django_blog` service.
    *   Mount the shared `postgres_db` network.
3.  **Proxy Config**: Update `traefik` labels on the new container to intercept traffic for the domain.

## 4. Schedule & Milestones
1.  **Week 1**: Init Django project, define Models, setup DB connection.
2.  **Week 2**: Extract HTML/CSS from WP, build `base.html` and list/detail views.
3.  **Week 3**: Write migration scripts, perform dry-run import, fix content formatting issues.
4.  **Week 4**: Finalize Docker setup, switch traffic, shut down WP container.

## 5. Key Considerations
*   **Permalinks**: WordPress URLs often look like `/2023/01/01/sample-post/`. We must match this regex in Django `urls.py` or create redirects.
*   **Passwords**: User passwords cannot be migrated directly due to different hashing. You will need to create a new superuser.
*   **Comments**: If using native WP comments, migration is complex. If using Disqus/Utterances, just copy the JS code.
