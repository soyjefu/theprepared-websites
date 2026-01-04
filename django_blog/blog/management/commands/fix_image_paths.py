from django.core.management.base import BaseCommand
from blog.models import Post

class Command(BaseCommand):
    help = 'Fix image paths in post content'

    def handle(self, *args, **options):
        posts = Post.objects.all()
        count = 0
        for post in posts:
            if '/wp-content/uploads/' in post.content:
                post.content = post.content.replace('/wp-content/uploads/', '/media/uploads/')
                post.save()
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Updated {count} posts with corrected image paths.'))
