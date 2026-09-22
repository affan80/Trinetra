from sqlalchemy import select
from backend.app.db.models import DuplicateCluster, DuplicateClusterMember, DuplicateType, ClusterStatus
from backend.app.dedup.clusters.representative import choose

DECISION_VERSION = "dedup-v1"

def find_cluster(db, record_id):
    member = db.scalar(select(DuplicateClusterMember).where(DuplicateClusterMember.record_id == record_id))
    return db.get(DuplicateCluster, member.cluster_id) if member else None

def assign(db, record, relationship: str, score: float, method: str, explanation: dict, cluster: DuplicateCluster | None = None):
    cluster = cluster or DuplicateCluster(cluster_type=relationship, representative_record_id=record.record_id, member_count=0, version=1, explanation={"method": "first_observation"})
    if cluster.id is None: db.add(cluster); db.flush()
    existing = db.scalar(select(DuplicateClusterMember).where(DuplicateClusterMember.cluster_id == cluster.id, DuplicateClusterMember.record_id == record.record_id))
    if not existing: db.add(DuplicateClusterMember(cluster_id=cluster.id, record_id=record.record_id, relationship_type=relationship, similarity_score=score, detection_method=method, decision_version=DECISION_VERSION, explanation=explanation)); cluster.member_count += 1
    representative = record if cluster.member_count == 1 else (choose(db, cluster.id) or record)
    cluster.representative_record_id = representative.record_id; cluster.updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc); cluster.version += 1
    return cluster
