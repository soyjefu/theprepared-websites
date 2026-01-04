import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from django.contrib.auth.models import User
from blog.models import Post, Category, Tag

class Command(BaseCommand):
    help = 'Import WordPress data from JSON files'

    def handle(self, *args, **options):
        base_dir = '/app/migration_tools/data'
        
        # Load data
        try:
            with open(os.path.join(base_dir, 'posts.json'), 'r', encoding='utf-8') as f:
                posts_data = json.load(f)
            with open(os.path.join(base_dir, 'terms.json'), 'r', encoding='utf-8') as f:
                terms_data = json.load(f)
            with open(os.path.join(base_dir, 'relationships.json'), 'r', encoding='utf-8') as f:
                rels_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('Data files not found in /app/migration_tools/data/'))
            return

        # 1. Setup User
        author, created = User.objects.get_or_create(username='admin')
        if created:
            author.set_password('admin')
            author.save()
            self.stdout.write(self.style.SUCCESS('Created default user "admin"'))

        # 2. Import Terms
        self.stdout.write('Importing terms...')
        category_map = {} # term_taxonomy_id -> Category object
        tag_map = {}      # term_taxonomy_id -> Tag object

        for term in terms_data:
            term_tax_id = term['term_taxonomy_id']
            name = term['name']
            slug = term['slug']
            taxonomy = term['taxonomy']

            if taxonomy == 'category':
                cat, _ = Category.objects.get_or_create(slug=slug, defaults={'name': name})
                category_map[term_tax_id] = cat
            elif taxonomy == 'post_tag':
                tag, _ = Tag.objects.get_or_create(slug=slug, defaults={'name': name})
                tag_map[term_tax_id] = tag

        self.stdout.write(self.style.SUCCESS(f'Imported {len(category_map)} categories and {len(tag_map)} tags.'))

        # 3. Import Posts
        self.stdout.write('Importing posts...')
        
        # Pre-process relationships for faster lookup
        # post_id -> list of term_taxonomy_ids
        post_rels = {}
        for rel in rels_data:
            pid = rel['object_id']
            tid = rel['term_taxonomy_id']
            if pid not in post_rels:
                post_rels[pid] = []
            post_rels[pid].append(tid)

        count = 0
        for p in posts_data:
            # Map fields
            title = p['post_title']
            content = p['post_content']
            slug = p['post_name']
            status = 'published' if p['post_status'] == 'publish' else 'draft'
            
            # Handle dates
            try:
                pub_date = datetime.strptime(p['post_date'], '%Y-%m-%d %H:%M:%S')
                pub_date = make_aware(pub_date)
            except (ValueError, TypeError):
                pub_date = make_aware(datetime.now())

            # Create Post
            post, created = Post.objects.get_or_create(
                slug=slug,
                defaults={
                    'title': title,
                    'content': content,
                    'author': author,
                    'status': status,
                    'published_at': pub_date,
                    'created_at': pub_date, # Approximation
                    'updated_at': make_aware(datetime.strptime(p['post_modified'], '%Y-%m-%d %H:%M:%S'))
                }
            )
            
            # Relationships
            wp_id = p['ID']
            if wp_id in post_rels:
                for tax_id in post_rels[wp_id]:
                    if tax_id in category_map:
                        post.categories.add(category_map[tax_id])
                    if tax_id in tag_map:
                        post.tags.add(tag_map[tax_id])
            
            post.save()
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} posts.'))
