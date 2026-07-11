# Neo4j Graph Schema

## Pipeline

```text
Scraper
   │
   ▼
Kafka
   │
   ▼
Spark Processing
   │
   ▼
Graph Loader
   │
   ▼
Neo4j Database
```

---

## Node Types

| Node | Properties |
|------|------------|
| Article | url, title, text, published_at |
| Author | name |
| Source | name, type |
| Topic | name |
| Person | name |
| Organization | name |
| Location | name |

---

## Edge Types

| From | Relationship | To |
|------|--------------|----|
| Author | WROTE | Article |
| Article | PUBLISHED_BY | Source |
| Article | HAS_TOPIC | Topic |
| Article | MENTIONS | Person |
| Article | MENTIONS | Organization |
| Article | LOCATED_IN | Location |

---

## Graph Structure

```text
Author
  |
 WROTE
  |
  ▼
Article ─────────► Source
   │                ▲
   │                │
HAS_TOPIC      PUBLISHED_BY
   │
   ▼
Topic

Article ──MENTIONS──► Person
Article ──MENTIONS──► Organization
Article ─LOCATED_IN─► Location
```

---

## Example Flow

```text
Input JSON
     │
     ▼
Spark Processing
     │
     ▼
Graph Loader
     │
     ▼
Neo4j Graph

Author → Article → Source
          │
          ├── Topic
          ├── Person
          ├── Organization
          └── Location
```