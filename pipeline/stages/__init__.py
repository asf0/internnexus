"""The pipeline's work stages, in execution order.

``ingest -> delete_inactive -> cleanup -> classify -> embed``

Each subpackage owns one stage. Machinery used by exactly one stage lives
inside it: ``ingest.sources`` (ATS adapters) and ``cleanup.location``
(location parsing).

Orchestration lives in :mod:`pipeline.runtime.orchestrator`; the canonical
step order is :data:`pipeline.runtime.step_order.PIPELINE_STEPS`.
"""
