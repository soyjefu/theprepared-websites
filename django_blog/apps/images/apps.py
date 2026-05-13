from django.apps import AppConfig


class ImagesConfig(AppConfig):
    name = "apps.images"
    label = "blog_images"
    verbose_name = "Images"

    def ready(self):
        from django.db.models.signals import post_save
        from .models import CustomImage
        from .signals import on_image_save
        post_save.connect(on_image_save, sender=CustomImage)
