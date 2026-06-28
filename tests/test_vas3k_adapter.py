from webclip.adapters.vas3k import Vas3kAdapter
from webclip.fetchers.base import FetchResult


def test_vas3k_adapter_matches_domain() -> None:
    adapter = Vas3kAdapter()
    assert adapter.matches("https://vas3k.club/post/123/")
    assert not adapter.matches("https://example.org/post/123/")


def test_vas3k_adapter_extracts_content_and_threaded_comments() -> None:
    html = """
    <html>
      <body>
        <h1 class="post-title">Гайд по релокации</h1>
        <section class="post-text">
          <div class="text-body text-body-type-post e-content">
            <p>Основной текст поста.</p>
            <p><img src="https://i.vas3k.club/post-image.jpg" alt="post image"></p>
          </div>
        </section>
        <div class="post-comments-list">
          <div class="comment" id="comment-parent-1">
            <a class="comment-header-author-name" href="/user/author/">Автор</a>
            <div class="comment-body">
              <div class="text-body text-body-type-comment"><p>Коммент 1</p></div>
            </div>
            <div class="comment-replies">
              <div class="reply" id="comment-child-1">
                <a class="comment-header-author-name" href="/user/replier/">Ответчик</a>
                <div class="text-body text-body-type-comment"><p>Ответ 1</p></div>
              </div>
            </div>
          </div>
        </div>
      </body>
    </html>
    """
    adapter = Vas3kAdapter()
    document = adapter.parse(
        FetchResult(
            url="https://vas3k.club/post/123/",
            final_url="https://vas3k.club/post/123/",
            status_code=200,
            html=html,
        )
    )

    assert document.metadata.title == "Гайд по релокации"
    assert len(document.content) >= 2
    assert len(document.comments) == 2
    parent = document.comments[0]
    reply = document.comments[1]
    assert parent.comment_id == "parent-1"
    assert reply.parent_id == "parent-1"
    assert str(document.assets[0].source_url) == "https://i.vas3k.club/post-image.jpg"
