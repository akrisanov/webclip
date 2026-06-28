from webclip.adapters.generic import GenericAdapter
from webclip.fetchers.base import FetchResult
from webclip.models import BlockType


def test_generic_adapter_extracts_title_blocks_and_assets() -> None:
    html = """
    <html>
      <head><title>Fallback Title</title></head>
      <body>
        <article>
          <h1>My Article</h1>
          <p>Hello world.</p>
          <img src="/img/example.png" alt="Example" />
        </article>
      </body>
    </html>
    """
    adapter = GenericAdapter()
    document = adapter.parse(
        FetchResult(
            url="https://example.org/post",
            final_url="https://example.org/post",
            status_code=200,
            html=html,
        )
    )

    assert document.metadata.title == "My Article"
    assert document.metadata.site == "example.org"
    assert len(document.content) >= 2
    assert any(block.type == BlockType.image for block in document.content)
    assert str(document.assets[0].source_url) == "https://example.org/img/example.png"
