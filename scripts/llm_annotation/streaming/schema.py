from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, confloat

Prob = confloat(ge=0.0, le=1.0)

EntityType = Literal["human", "non-human"]

OrganizationType = Literal[
    "not_applicable",
    "religious",
    "state",
    "cooperative",
    "commercial",
    "commercial_farm",
    "educational",
    "trust_ngo",
    "other",
    "cannot_decide",
]

GenderLabel = Literal["cannot decide", "man", "woman"]
ReligionLabel = Literal["cannot decide", "hindu", "muslim", "other religion"]


class IndexedNameAnnotationResponse(BaseModel):
    idx: int

    entity_type: EntityType
    entity_confidence: Prob

    organization_type: OrganizationType
    organization_confidence: Prob

    gender: GenderLabel
    prop_women: Optional[Prob] = None

    religion: ReligionLabel
    prop_hindu: Prob
    prop_muslim: Prob


class BatchAnnotationResponse(BaseModel):
    annotations: List[IndexedNameAnnotationResponse]


class NameAnnotationRecord(BaseModel):
    idx: int  # local to the batch; for auditing
    name: str

    entity_type: EntityType
    entity_confidence: float

    organization_type: OrganizationType
    organization_confidence: float

    gender: GenderLabel
    prop_women: Optional[float] = None

    religion: ReligionLabel
    prop_hindu: float
    prop_muslim: float

    @classmethod
    def from_idx_and_ann(cls, name: str, idx: int, ann: IndexedNameAnnotationResponse) -> "NameAnnotationRecord":
        return cls(
            idx=idx,
            name=name,
            entity_type=ann.entity_type,
            entity_confidence=float(ann.entity_confidence),
            organization_type=ann.organization_type,
            organization_confidence=float(ann.organization_confidence),
            gender=ann.gender,
            prop_women=None if ann.prop_women is None else float(ann.prop_women),
            religion=ann.religion,
            prop_hindu=float(ann.prop_hindu),
            prop_muslim=float(ann.prop_muslim),
        )