import scrapy

class NewsItem(scrapy.Item):
    source_name = scrapy.Field()
    source_type = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    text = scrapy.Field()
    author = scrapy.Field()
    published_at = scrapy.Field()
    country_tags = scrapy.Field()
    topic_tags = scrapy.Field()
    metadata = scrapy.Field()

class BlogItem(scrapy.Item):
    source_name = scrapy.Field()
    source_type = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    text = scrapy.Field()
    author = scrapy.Field()
    published_at = scrapy.Field()
    country_tags = scrapy.Field()
    topic_tags = scrapy.Field()
    metadata = scrapy.Field()

class ImageItem(scrapy.Item):
    source_name = scrapy.Field()
    source_type = scrapy.Field()
    page_url = scrapy.Field()
    image_url = scrapy.Field()
    image_urls = scrapy.Field()
    images = scrapy.Field()
    title = scrapy.Field()
    alt = scrapy.Field()
    caption = scrapy.Field()
    metadata = scrapy.Field()
