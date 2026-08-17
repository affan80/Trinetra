SPIDER_MODULES = ["services.ingestion.crawlers.spiders"]
NEWSPIDER_MODULE = "services.ingestion.crawlers.spiders"

ITEM_PIPELINES = {
    "services.processing.parser.pipelines.EnrichmentPipeline": 250,
    "services.processing.parser.pipelines_ner.EntityExtractionPipeline": 275,
    "services.processing.parser.pipelines.OsintPipeline": 300,
    "services.processing.parser.pipelines.KafkaPipeline": 400,
    "services.processing.parser.pipelines.DLQPipeline": 500,
}
