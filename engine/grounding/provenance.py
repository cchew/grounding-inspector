from contextlib import contextmanager
from datetime import datetime, timezone

from prov.model import ProvDocument


class ProvenanceRecorder:
    """Wraps a prov.model.ProvDocument. Call sites record Activities/Entities/
    Agents as pipeline stages run; nothing here changes existing function
    signatures except label_claims's new optional `recorder` parameter.

    prov's ProvDocument.entity()/.agent() are not idempotent -- calling
    either twice with the same identifier creates two duplicate records
    (confirmed against the real library). Entities and Agents are memoised
    here by id so the same model or the same source document referenced
    across many claims becomes one node in the graph, not one per call.
    """

    def __init__(self, fixture_id: str):
        self.doc = ProvDocument()
        self.doc.set_default_namespace("https://grounding-inspector.dev/prov/")
        self.fixture_id = fixture_id
        self._agents: dict[str, object] = {}
        self._entities: dict[str, object] = {}

    def _entity(self, entity_id: str, attrs: dict | None = None):
        if entity_id not in self._entities:
            self._entities[entity_id] = self.doc.entity(entity_id, attrs)
        return self._entities[entity_id]

    def _agent(self, agent_id: str, attrs: dict | None = None):
        if agent_id not in self._agents:
            self._agents[agent_id] = self.doc.agent(agent_id, attrs)
        return self._agents[agent_id]

    @contextmanager
    def activity(self, kind: str, qualifier: str, agent_id: str, agent_attrs: dict | None = None):
        """Context manager: records start/end time, an Activity named
        f"{kind}_{qualifier}" (e.g. "verify_c2", "decompose_travel-pds-01"),
        and an Agent (memoised by agent_id). Yields the ProvActivity handle
        for use with record_used/record_generated."""
        activity_id = f"{kind}_{qualifier}"
        start = datetime.now(timezone.utc)
        act = self.doc.activity(activity_id, start)
        agent = self._agent(agent_id, agent_attrs)
        self.doc.wasAssociatedWith(act, agent)
        try:
            yield act
        finally:
            act.set_time(endTime=datetime.now(timezone.utc))

    def record_used(self, activity, entity_id: str):
        self._entity(entity_id)
        self.doc.used(activity, entity_id)

    def record_generated(self, activity, entity_id: str, entity_attrs: dict | None = None):
        self._entity(entity_id, entity_attrs)
        self.doc.wasGeneratedBy(entity_id, activity)

    def record_derived(self, entity_id: str, from_entity_ids: list[str]):
        self._entity(entity_id)
        for src in from_entity_ids:
            self.doc.wasDerivedFrom(entity_id, src)

    def serialize(self, path):
        self.doc.serialize(destination=str(path), format="json")
