## what pattern palantir use

<!-- 1. ELT and ETL: -->

## what is ELT
ELT == Extract => Load => Transform 

## what is ETL
ETL == Extract => Transform => Load

## we will gonna use ELT 

### why ELT:
** we will collect data from news/blogs/socal media and dark/ **
# which mean data will be (messey, unstructred, fake, incomplete, useful later, diffreant formats, multi language, duplicate heavy) #

Exmeple:
Raw article contains:
- original title
- HTML metadata
- author
- image URL
- publish timestamp
- edited timestamp
- hidden tags
- source layout


### why not ETL:
# May be we will use this but not now bescusse ETL is good when data is (Data format is fixed / Data is clean / You already know the schema / You do not need raw evidence much)


### Connecting to data ###

## Data Connection :
The Data (Connection framework) is designed to manage data over time, through discrete versions that are managed using (dataset transactions) this framework enables full lineage of data versions across time, providing you with an understanding of which sync tasks produced which versions of a given dataset it also enables syncing of only the data required, in cases where full data loading on each sync is not possible.

# why we are usning data connection framework
- Instead of relying on messy, customized code scripts for every single integration
- for data connection orgs like palantir etc use Data collectioin farame works like (Appache Kafka) but palantir has there own Frame work.
- So we will gonna use (Appache Kafa) becausse its open sourece and free

# what is Connectioin framework and how this works:
- a structured architecture of tools, protocols, and rules that allows different software applications, databases, and cloud services to securely exchange and synchronize data
- this all are managed using dataset transactions

## data Piplines ##

# but palantir has onotoly and kafka does not

# what is onotoly:
- ontology is a formal machine-readable model that defines the concepts, data, or objects within a specific area and maps the precise relationships between them and this workslike graph dbs

# we can use Graph DB for this

# Data qulity:
Cleaning and normalizing data is a core part of the pipeline building process we can use (Appahe spark) for this

# Data lineage:
the process of tracking the end-to-end journey of data from its origin, through all transformations and systems, to its final destination

# Change data capture (CDC):
CDC is an enterprise data integration pattern often used to stream real-time updates from a relational database to other consumers
