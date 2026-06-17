SPIDER_MODULES = ["services.crawlers.spiders"]
NEWSPIDER_MODULE = "services.crawlers.spiders"

ITEM_PIPELINES = {
    "services.parser.pipelines.OsintPipeline": 300,
    "services.parser.pipelines.KafkaPipeline": 400,
}
