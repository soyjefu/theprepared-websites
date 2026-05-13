from django.apps import AppConfig


class MigrationConfig(AppConfig):
    name = "apps.migration"
    label = "blog_migration"
    verbose_name = "WordPress Migration"
