from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class VisitorIdentity(models.Model):
    """비회원 방문자 식별. visitor_token 쿠키(원본은 클라이언트에만)의 해시를 저장."""

    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    nickname = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True)  # 옵션, 답글 알림용. 노출 X
    ip_hash = models.CharField(max_length=64, db_index=True)
    user_agent_hash = models.CharField(max_length=64, blank=True)
    is_trusted = models.BooleanField(
        default=False,
        help_text="approved 댓글 N건 이상이면 자동 승격",
    )
    is_blocked = models.BooleanField(default=False)
    notify_replies = models.BooleanField(default=False, help_text="답글 알림 옵트인")
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    nickname_changed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.nickname} (visitor#{self.pk})"


class BlockedIdentifier(models.Model):
    """관리자가 영구 차단한 식별자."""

    KIND_IP = "ip"
    KIND_EMAIL = "email"
    KIND_NICKNAME = "nick"
    KIND_CHOICES = [
        (KIND_IP, "IP"),
        (KIND_EMAIL, "Email"),
        (KIND_NICKNAME, "Nickname"),
    ]

    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    value_hash = models.CharField(max_length=64)
    reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["kind", "value_hash"], name="uniq_blocked"),
        ]


class Comment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_SPAM = "spam"
    STATUS_DELETED = "deleted"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_SPAM, "Spam"),
        (STATUS_DELETED, "Deleted"),
    ]

    page = models.ForeignKey(
        "wagtailcore.Page",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    parent = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    visitor = models.ForeignKey(
        VisitorIdentity, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="comments",
    )
    admin_user = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="admin_comments",
        help_text="관리자가 작성한 답글",
    )
    nickname_snapshot = models.CharField(max_length=20)  # 작성 시점 닉네임 박제
    body = models.TextField()                            # plain (bleach strip-all)
    body_html = models.TextField()                       # 캐시된 안전 렌더 (autolink)
    ip_hash = models.CharField(max_length=64)
    user_agent_hash = models.CharField(max_length=64, blank=True)
    spam_score = models.FloatField(default=0.0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_APPROVED)
    moderation_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["page", "status", "created_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["page", "ip_hash", "body"],
                name="uniq_dup_comment",
            ),
        ]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"#{self.pk} {self.nickname_snapshot}: {self.body[:30]}"


class PageView(models.Model):
    """글 조회수 — IP 기반 일일 1회 카운트 (관리자만 노출)."""

    page = models.ForeignKey(
        "wagtailcore.Page",
        on_delete=models.CASCADE,
        related_name="page_views",
    )
    ip_hash = models.CharField(max_length=64)
    date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["page", "ip_hash", "date"],
                name="uniq_view_per_ip_per_day",
            ),
        ]
        indexes = [
            models.Index(fields=["page", "date"]),
            models.Index(fields=["date"]),
        ]


class PostLike(models.Model):
    """글 공감 (♥). visitor_token 또는 IP 기반 UNIQUE — 한 사람 1회."""

    page = models.ForeignKey(
        "wagtailcore.Page",
        on_delete=models.CASCADE,
        related_name="likes",
    )
    visitor = models.ForeignKey(
        VisitorIdentity, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="likes",
    )
    ip_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["page", "ip_hash"],
                name="uniq_like_per_ip_per_page",
            ),
        ]
        indexes = [models.Index(fields=["page"])]
