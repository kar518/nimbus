"""
Service layer: business logic that orchestrates models, external calls,
and background jobs on behalf of the API and Celery tasks.

Nothing here yet by design — endpoints and tasks should call into services
rather than embedding logic directly, once that logic is implemented.
"""
