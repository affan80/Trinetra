SPIDER_MODULES = ["services.crawlers.spiders"]
NEWSPIDER_MODULE = "services.crawlers.spiders"

ITEM_PIPELINES = {
    "services.parser.pipelines.EnrichmentPipeline": 250,
    "services.parser.pipelines_ner.EntityExtractionPipeline": 275,
    "services.parser.pipelines.OsintPipeline": 300,
    "services.parser.pipelines.KafkaPipeline": 400,
    "services.parser.pipelines.DLQPipeline": 500,
}
