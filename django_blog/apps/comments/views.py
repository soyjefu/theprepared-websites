"""댓글 작성 / 삭제 뷰. 로그인 없음 — visitor_token 쿠키로 식별."""
from __future__ import annotations

import logging
from datetime import timedelta

from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit
from wagtail.models import Page

from .forms import CommentForm
from .models import BlockedIdentifier, Comment, PostLike, VisitorIdentity
from .utils import (
    get_client_ip,
    heuristic_spam_score,
    ip_hash,
    make_visitor_token,
    sanitize_body,
    ua_hash,
    verify_form_token,
    visitor_token_hash,
)

log = logging.getLogger(__name__)
COOKIE_NAME = "vid_token"


def _resolve_visitor(request) -> VisitorIdentity | None:
    raw = request.COOKIES.get(COOKIE_NAME)
    if not raw:
        return None
    return VisitorIdentity.objects.filter(token_hash=visitor_token_hash(raw)).first()


def _is_blocked(ip_h: str, email: str = "", nickname: str = "") -> bool:
    from .utils import hmac_hash
    qs = []
    if ip_h:
        qs.append(("ip", ip_h))
    if email:
        qs.append(("email", hmac_hash(email.lower(), salt="email")))
    if nickname:
        qs.append(("nick", hmac_hash(nickname.lower(), salt="nick")))
    for kind, vh in qs:
        if BlockedIdentifier.objects.filter(kind=kind, value_hash=vh).exists():
            return True
    return False


@require_POST
@ratelimit(key="ip", rate="5/10m", block=False)
@ratelimit(key="ip", rate="1/m", block=False)
def submit(request):
    if getattr(request, "limited", False):
        messages.error(request, "잠시 후 다시 시도해주세요.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    form = CommentForm(request.POST)
    if not form.is_valid():
        messages.error(request, "댓글 형식이 잘못되었습니다.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    cd = form.cleaned_data

    # honeypot
    if cd.get("website"):
        log.info("honeypot trigger ip=%s", get_client_ip(request))
        return redirect(request.META.get("HTTP_REFERER", "/"))  # 조용히 무시

    # time-trap (사용자가 form_token 비활성 상태로 빠르게 제출하면 봇)
    elapsed = verify_form_token(cd.get("form_token", ""))
    if elapsed is None:
        # form_token 미발급/만료/너무 빠름 — pending 처리(reject 아님, 너그럽게)
        spam_extra = 0.3
    else:
        spam_extra = 0.0

    page = get_object_or_404(Page.objects.live(), pk=cd["page_id"])
    parent_id = cd.get("parent_id")
    parent = Comment.objects.filter(pk=parent_id, page=page).first() if parent_id else None

    ip = get_client_ip(request)
    iph = ip_hash(ip)
    uah = ua_hash(request.META.get("HTTP_USER_AGENT", ""))

    visitor = _resolve_visitor(request)
    new_token_raw = None
    if visitor is None:
        nickname = (cd.get("nickname") or "").strip()
        if not nickname:
            messages.error(request, "닉네임을 입력해주세요 (최초 1회).")
            return redirect(request.META.get("HTTP_REFERER", "/"))
        if VisitorIdentity.objects.filter(nickname__iexact=nickname).exists():
            messages.error(request, f"닉네임 '{nickname}'은 이미 사용 중입니다.")
            return redirect(request.META.get("HTTP_REFERER", "/"))
        if _is_blocked(iph, cd.get("email", ""), nickname):
            return HttpResponseBadRequest("blocked")
        raw, h = make_visitor_token()
        new_token_raw = raw
        visitor = VisitorIdentity.objects.create(
            token_hash=h,
            nickname=nickname[:20],
            email=(cd.get("email") or "").strip(),
            ip_hash=iph,
            user_agent_hash=uah,
            notify_replies=bool(cd.get("notify_replies")),
        )
    else:
        if visitor.is_blocked or _is_blocked(iph, visitor.email, visitor.nickname):
            return HttpResponseBadRequest("blocked")
        # last_seen 갱신
        visitor.ip_hash = iph
        visitor.last_seen_at = timezone.now()
        visitor.save(update_fields=["ip_hash", "last_seen_at"])

    plain, html = sanitize_body(cd["body"])
    score, reason = heuristic_spam_score(plain)
    score = min(score + spam_extra, 1.0)

    if score >= 0.7:
        status = Comment.STATUS_SPAM
    elif score >= 0.3 or not visitor.is_trusted:
        status = Comment.STATUS_PENDING if score >= 0.3 else Comment.STATUS_APPROVED
    else:
        status = Comment.STATUS_APPROVED

    # 신뢰 사용자 빠른 자동 승인
    if visitor.is_trusted and score < 0.3:
        status = Comment.STATUS_APPROVED

    try:
        comment = Comment.objects.create(
            page=page,
            parent=parent,
            visitor=visitor,
            nickname_snapshot=visitor.nickname,
            body=plain,
            body_html=html,
            ip_hash=iph,
            user_agent_hash=uah,
            spam_score=score,
            status=status,
            moderation_reason=reason,
        )
    except Exception as e:
        log.warning("댓글 저장 실패 (중복 가능성): %s", e)
        messages.error(request, "이미 같은 내용을 작성하셨습니다.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    # 자동 승격: approved 댓글 ≥ 3건이면 trusted
    if not visitor.is_trusted:
        if visitor.comments.filter(status=Comment.STATUS_APPROVED).count() >= 3:
            visitor.is_trusted = True
            visitor.save(update_fields=["is_trusted"])

    # 알림 (status=approved일 때만 비동기 enqueue)
    if status == Comment.STATUS_APPROVED:
        try:
            from .tasks import notify_new_comment
            notify_new_comment.delay(comment.pk)
        except Exception as e:
            log.warning("notify task enqueue 실패: %s", e)

    if status == Comment.STATUS_PENDING:
        messages.info(request, "댓글이 검토 대기 중입니다.")
    elif status == Comment.STATUS_SPAM:
        messages.warning(request, "댓글이 차단되었습니다.")
    else:
        messages.success(request, "댓글이 등록되었습니다.")

    response = redirect(f"{page.url}#comment-{comment.pk}" if status != Comment.STATUS_SPAM else page.url)
    if new_token_raw:
        response.set_cookie(
            COOKIE_NAME, new_token_raw,
            max_age=60 * 60 * 24 * 365,
            httponly=True,
            secure=not request.scheme == "http",  # dev http에서도 OK
            samesite="Lax",
        )
    return response


@require_POST
@ratelimit(key="ip", rate="60/h", block=False)
def toggle_like(request, page_id: int):
    """공감 토글. 같은 IP가 글에 1회. 다시 누르면 해제."""
    from django.http import JsonResponse
    if getattr(request, "limited", False):
        return JsonResponse({"error": "rate limit"}, status=429)
    page = get_object_or_404(Page.objects.live(), pk=page_id)
    iph = ip_hash(get_client_ip(request))
    visitor = _resolve_visitor(request)
    existing = PostLike.objects.filter(page=page, ip_hash=iph).first()
    if existing:
        existing.delete()
        liked = False
    else:
        PostLike.objects.create(page=page, visitor=visitor, ip_hash=iph)
        liked = True
    count = PostLike.objects.filter(page=page).count()
    if request.headers.get("X-Requested-With") == "fetch":
        return JsonResponse({"liked": liked, "count": count})
    return redirect(f"{page.url}#like")


def _can_manage(request, comment) -> bool:
    """관리자(staff) 또는 visitor_token 매치 시 본인."""
    if request.user.is_authenticated and request.user.is_staff:
        return True
    visitor = _resolve_visitor(request)
    if visitor is not None and comment.visitor_id == visitor.id:
        return True
    return False


@require_POST
@ratelimit(key="ip", rate="20/h", block=True)
def delete_own(request, comment_id: int):
    """관리자 또는 본인(visitor_token 매치) 삭제."""
    comment = get_object_or_404(Comment, pk=comment_id)
    if not _can_manage(request, comment):
        return HttpResponseBadRequest("권한 없음")
    is_admin = request.user.is_authenticated and request.user.is_staff
    if not is_admin and comment.created_at < timezone.now() - timedelta(days=30):
        return HttpResponseBadRequest("30일 이상 지난 댓글은 삭제할 수 없습니다.")

    page_url = comment.page.url
    # 자식 답글이 있으면 soft delete (스레드 구조 유지), 없으면 hard delete
    if comment.replies.exists():
        # UNIQUE(page, ip_hash, body) 충돌 회피 위해 PK 포함 placeholder
        comment.status = Comment.STATUS_DELETED
        comment.body = f"[삭제된 댓글 #{comment.pk}]"
        comment.body_html = '<span style="color: var(--color-muted);">삭제된 댓글입니다.</span>'
        comment.save(update_fields=["status", "body", "body_html", "updated_at"])
    else:
        comment.delete()
    messages.success(request, "댓글이 삭제되었습니다.")
    return redirect(page_url + "#comments")


@require_POST
@ratelimit(key="ip", rate="5/d", block=True)
def change_nickname(request):
    """방문자 닉네임 변경 — 7일 1회 + UNIQUE."""
    from datetime import timedelta as td
    visitor = _resolve_visitor(request)
    if visitor is None:
        return HttpResponseBadRequest("쿠키가 없습니다 — 댓글을 한 번 작성하면 닉네임이 발급됩니다.")
    if visitor.nickname_changed_at:
        elapsed = timezone.now() - visitor.nickname_changed_at
        if elapsed < td(days=7):
            remain = 7 - elapsed.days
            messages.error(request, f"닉네임은 7일에 1회만 변경할 수 있습니다. ({remain}일 남음)")
            return redirect(request.META.get("HTTP_REFERER", "/"))
    new = (request.POST.get("nickname") or "").strip()[:20]
    if not new:
        messages.error(request, "닉네임을 입력해주세요.")
        return redirect(request.META.get("HTTP_REFERER", "/"))
    if new == visitor.nickname:
        messages.info(request, "기존 닉네임과 같습니다.")
        return redirect(request.META.get("HTTP_REFERER", "/"))
    if VisitorIdentity.objects.exclude(pk=visitor.pk).filter(nickname__iexact=new).exists():
        messages.error(request, f"‘{new}’은 이미 사용 중인 닉네임입니다.")
        return redirect(request.META.get("HTTP_REFERER", "/"))
    visitor.nickname = new
    visitor.nickname_changed_at = timezone.now()
    visitor.save(update_fields=["nickname", "nickname_changed_at"])
    messages.success(request, f"닉네임을 ‘{new}’로 변경했습니다.")
    return redirect(request.META.get("HTTP_REFERER", "/"))


@require_POST
@ratelimit(key="ip", rate="20/h", block=True)
def update_own(request, comment_id: int):
    """관리자 또는 본인(visitor_token 매치) 수정."""
    comment = get_object_or_404(Comment, pk=comment_id)
    if not _can_manage(request, comment):
        return HttpResponseBadRequest("권한 없음")
    new_body = (request.POST.get("body") or "").strip()
    if not new_body:
        return HttpResponseBadRequest("본문이 비어있습니다.")
    plain, html = sanitize_body(new_body)
    comment.body = plain
    comment.body_html = html
    comment.save(update_fields=["body", "body_html", "updated_at"])
    messages.success(request, "댓글이 수정되었습니다.")
    return redirect(f"{comment.page.url}#comment-{comment.pk}")
