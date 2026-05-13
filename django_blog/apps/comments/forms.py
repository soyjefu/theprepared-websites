from django import forms

from .models import Comment


class CommentForm(forms.Form):
    nickname = forms.CharField(
        max_length=20, required=False,
        help_text="처음 작성하시면 닉네임을 정해주세요.",
    )
    email = forms.EmailField(
        required=False,
        help_text="(선택) 답글 알림 받기 — 비공개",
    )
    body = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "댓글을 남겨주세요"}),
        max_length=5000, required=True,
    )
    parent_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    page_id = forms.IntegerField(required=True, widget=forms.HiddenInput)
    notify_replies = forms.BooleanField(required=False, label="답글 알림 받기")

    # 봇 방지
    website = forms.CharField(required=False, widget=forms.HiddenInput)  # honeypot
    form_token = forms.CharField(required=False, widget=forms.HiddenInput)
