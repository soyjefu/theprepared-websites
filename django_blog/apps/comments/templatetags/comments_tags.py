from collections import defaultdict

from django import template

from apps.comments.forms import CommentForm
from apps.comments.models import Comment, VisitorIdentity
from apps.comments.utils import make_form_token, visitor_token_hash

register = template.Library()


@register.inclusion_tag("comments/thread.html", takes_context=True)
def render_comments(context, page):
    request = context["request"]

    # 1) approved 댓글 모두
    approved = list(
        Comment.objects.filter(page=page, status=Comment.STATUS_APPROVED)
        .select_related("visitor", "admin_user", "parent")
    )
    # 2) approved의 부모 중 status=deleted인 placeholder도 포함 (자식 트리 유지)
    parent_ids = {c.parent_id for c in approved if c.parent_id}
    deleted_parents = list(
        Comment.objects.filter(pk__in=parent_ids, status=Comment.STATUS_DELETED)
        .select_related("visitor", "admin_user", "parent")
    )

    all_comments = sorted(approved + deleted_parents, key=lambda c: c.created_at)

    children = defaultdict(list)
    roots = []
    for c in all_comments:
        if c.parent_id and any(p.pk == c.parent_id for p in all_comments):
            children[c.parent_id].append(c)
        else:
            roots.append(c)

    raw = request.COOKIES.get("vid_token")
    visitor = None
    if raw:
        visitor = VisitorIdentity.objects.filter(token_hash=visitor_token_hash(raw)).first()

    form_token = make_form_token()
    is_admin = bool(request.user.is_authenticated and request.user.is_staff)
    visitor_id = visitor.id if visitor else None
    return {
        "page": page,
        "roots": roots,
        "children": dict(children),
        "form": CommentForm(initial={"page_id": page.pk, "form_token": form_token}),
        "form_token": form_token,
        "visitor": visitor,
        "visitor_id": visitor_id,
        "is_admin": is_admin,
        "approved_count": len(approved),
    }
