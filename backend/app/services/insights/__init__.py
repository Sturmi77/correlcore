"""Insight engine families (#777).

The former ~1.8k-line ``insight_engine`` module is split here by insight family.
Shared data structures and helpers live in :mod:`app.services.insights.shared`;
each family module exposes pure ``*_candidates`` functions consumed by the thin
orchestrator in :mod:`app.services.insight_engine`, which remains the public
entry point (and re-exports the names this package defines for backwards
compatibility).
"""
