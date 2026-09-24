SPIDER_MODULES = ["services.ingestion.crawlers.spiders"]
NEWSPIDER_MODULE = "services.ingestion.crawlers.spiders"
TELNETCONSOLE_ENABLED = False

ITEM_PIPELINES = {
    "services.processing.parser.pipelines.EnrichmentPipeline": 250,
    "services.processing.parser.pipelines.OsintPipeline": 300,
    "services.processing.parser.pipelines.DLQPipeline": 500,
}
