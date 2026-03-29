"""Job state management. V1: in-memory dict. V2: Redis."""

# V1: Simple in-memory store
# V2'de bu Redis'e taşınacak, aynı interface kalacak
job_store: dict[str, dict] = {}
