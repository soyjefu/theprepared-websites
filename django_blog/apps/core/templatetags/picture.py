"""<picture> 태그 — AVIF/WebP/원본 fallback + srcset 반응형."""
from __future__ import annotations

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

SRCSET_WIDTHS = [400, 800, 1200]


@register.simple_tag
def picture(
    image,
    spec: str = "width-800",
    alt: str = "",
    css_class: str = "",
    loading: str = "lazy",
    lightbox: bool = False,
    srcset: bool = True,
):
    if image is None:
        return ""
    try:
        fb = image.get_rendition(spec)
        avif_default = image.get_rendition(f"{spec}|format-avif")
        webp_default = image.get_rendition(f"{spec}|format-webp")
    except Exception:
        return ""

    alt_text = alt or getattr(image, "alt_text", "") or image.title or ""
    cls = f' class="{css_class}"' if css_class else ""

    data_full = ""
    if lightbox:
        try:
            full = image.get_rendition("width-1920")
            data_full = f' data-full="{full.url}" data-alt="{alt_text}"'
        except Exception:
            pass

    avif_srcset = avif_default.url
    webp_srcset = webp_default.url
    sizes_attr = ""
    if srcset and spec.startswith("width-"):
        widths = [w for w in SRCSET_WIDTHS if w <= (image.width or 99999)]
        if len(widths) >= 2:
            try:
                avif_parts = []
                webp_parts = []
                for w in widths:
                    a = image.get_rendition(f"width-{w}|format-avif")
                    wp = image.get_rendition(f"width-{w}|format-webp")
                    avif_parts.append(f"{a.url} {w}w")
                    webp_parts.append(f"{wp.url} {w}w")
                avif_srcset = ", ".join(avif_parts)
                webp_srcset = ", ".join(webp_parts)
                sizes_attr = ' sizes="(max-width: 768px) 100vw, 720px"'
            except Exception:
                pass

    return mark_safe(
        f'<picture{cls}{data_full}>'
        f'<source type="image/avif" srcset="{avif_srcset}"{sizes_attr}>'
        f'<source type="image/webp" srcset="{webp_srcset}"{sizes_attr}>'
        f'<img src="{fb.url}" alt="{alt_text}" loading="{loading}" '
        f'decoding="async" width="{fb.width}" height="{fb.height}">'
        f'</picture>'
    )


@register.simple_tag(takes_context=True)
def og_image_url(context, image):
    """OG/Twitter용 1200x630 절대 URL. 이미지 없으면 빈 문자열."""
    if image is None:
        return ""
    try:
        r = image.get_rendition("fill-1200x630")
    except Exception:
        return ""
    request = context.get("request")
    if request is None:
        return r.url
    return f"{request.scheme}://{request.get_host()}{r.url}"
