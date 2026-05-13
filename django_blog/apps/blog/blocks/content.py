"""StreamField 블록 정의 — Gutenberg 매핑.

각 블록은 admin preview를 위해 template 기반 렌더 사용.
Phase별로 점진 확장 (지도/표/컬럼 등은 후속 Phase에서 추가).
"""
from wagtail import blocks
from wagtail.embeds.blocks import EmbedBlock
from wagtail.images.blocks import ImageChooserBlock

from .map_block import MapBlock


class HeadingBlock(blocks.StructBlock):
    text = blocks.CharBlock(required=True, max_length=200)
    level = blocks.ChoiceBlock(
        choices=[("h2", "H2"), ("h3", "H3"), ("h4", "H4")],
        default="h2",
    )
    anchor = blocks.CharBlock(
        required=False,
        max_length=80,
        help_text="비워두면 자동 슬러그",
    )

    class Meta:
        icon = "title"
        template = "blog/blocks/heading.html"
        preview_template = "blog/blocks/heading.html"
        preview_value = {"text": "예시 헤딩", "level": "h2"}
        label = "헤딩"


class ParagraphBlock(blocks.RichTextBlock):
    class Meta:
        icon = "pilcrow"
        template = "blog/blocks/paragraph.html"
        features = ["bold", "italic", "link", "ol", "ul", "hr", "code"]
        label = "본문"


class ImageBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=True)
    caption = blocks.CharBlock(required=False, max_length=200)
    alt_override = blocks.CharBlock(required=False, max_length=200,
                                    help_text="비워두면 이미지의 alt 사용")
    link = blocks.URLBlock(required=False)

    class Meta:
        icon = "image"
        template = "blog/blocks/image.html"
        preview_template = "blog/blocks/image.html"
        label = "이미지"


class QuoteBlock(blocks.StructBlock):
    text = blocks.TextBlock(required=True)
    attribution = blocks.CharBlock(required=False, max_length=200)

    class Meta:
        icon = "openquote"
        template = "blog/blocks/quote.html"
        preview_template = "blog/blocks/quote.html"
        preview_value = {"text": "준비된 자가 기회를 잡는다.", "attribution": "익명"}
        label = "인용"


class CodeBlock(blocks.StructBlock):
    language = blocks.CharBlock(required=False, max_length=30, default="python")
    code = blocks.TextBlock(required=True)

    class Meta:
        icon = "code"
        template = "blog/blocks/code.html"
        preview_value = {"language": "python", "code": "print('hello')"}
        label = "코드"


class ContentStreamBlock(blocks.StreamBlock):
    """Gutenberg-like 본문 스트림."""
    heading = HeadingBlock()
    paragraph = ParagraphBlock()
    image = ImageBlock()
    quote = QuoteBlock()
    code = CodeBlock()
    embed = EmbedBlock(
        icon="media",
        template="blog/blocks/embed.html",
        label="임베드 (YouTube/Vimeo/네이버TV…)",
    )
    map = MapBlock()

    class Meta:
        block_counts = {}
