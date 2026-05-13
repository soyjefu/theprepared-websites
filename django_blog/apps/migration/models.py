from django.db import models


class MigrationMap(models.Model):
    """WordPress 객체 ↔ Wagtail 객체 매핑 (멱등성 보장)."""

    KIND_POST = "post"
    KIND_PAGE = "page"
    KIND_ATTACHMENT = "attachment"
    KIND_CATEGORY = "category"
    KIND_TAG = "tag"
    KIND_USER = "user"
    KIND_CHOICES = [
        (KIND_POST, "Post"),
        (KIND_PAGE, "Page"),
        (KIND_ATTACHMENT, "Attachment"),
        (KIND_CATEGORY, "Category"),
        (KIND_TAG, "Tag"),
        (KIND_USER, "User"),
    ]

    wp_id = models.IntegerField()
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    wagtail_pk = models.IntegerField(help_text="대응 Wagtail/Django 모델의 PK")
    wagtail_model = models.CharField(
        max_length=80,
        help_text="예: 'blog.BlogPostPage', 'blog_images.CustomImage'",
    )
    extra = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["kind", "wp_id"], name="uniq_wp_obj"),
        ]
        indexes = [
            models.Index(fields=["wagtail_model", "wagtail_pk"]),
        ]

    def __str__(self) -> str:
        return f"{self.kind}#{self.wp_id} -> {self.wagtail_model}#{self.wagtail_pk}"


class MigrationRun(models.Model):
    """import 실행 기록 (감사용)."""
    command = models.CharField(max_length=80)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    success = models.BooleanField(default=False)
    counters = models.JSONField(default=dict)  # {created, updated, skipped, errors}
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
