import json


class NewsPipeline:
    def open_spider(self, spider):
        """
        This runs one time when the spider starts.
        It opens a JSONL file for saving scraped news data.
        """
        self.file = open("news_data.jsonl", "w", encoding="utf-8")

    def process_item(self, item, spider):
        """
        This runs every time the spider yields one article.
        It saves the article data into news_data.jsonl.
        """
        article = dict(item)

        # Optional: skip empty articles
        if not article.get("title") and not article.get("text"):
            return item

        line = json.dumps(article, ensure_ascii=False)
        self.file.write(line + "\n")

        return item

    def close_spider(self, spider):
        """
        This runs one time when the spider finishes.
        It closes the file safely.
        """
        self.file.close()
