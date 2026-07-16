import json

CACHED_ARTICLE_PATH = "./cached_articles/article_{}.json"
STATIC_DIR_PATH = "./static/"
ARTICLE_FILE_PATTERN = "article_{}.json"

for i in range(1, 44, 1):
    cached_article = CACHED_ARTICLE_PATH.format(i)
    with open(cached_article, "r", encoding='utf-8') as cached_file:
        article = json.load(cached_file)
        content = article["content"]

        article_file = ARTICLE_FILE_PATTERN.format(i)#.replace("json", "html")
        with open(f"{STATIC_DIR_PATH}{article_file}.html", "w", encoding='utf-8') as f:
            f.write(f"""
                {content}
            """)


