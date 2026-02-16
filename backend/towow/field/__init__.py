"""
V2 Intent Field module.

Core exports:
  - IntentField: Protocol (deposit, match, match_owners)
  - MemoryField: In-memory implementation
  - FieldResult, OwnerMatch, Intent: Data types
  - EncodingPipeline, MpnetEncoder, SimHashProjector: Encoding stack
  - profile_to_text, load_all_profiles: Profile loading utilities (preserved from V1)
"""

from towow.field.types import FieldResult, Intent, OwnerMatch
from towow.field.protocols import IntentField, Encoder, Projector
from towow.field.field import MemoryField
from towow.field.encoder import MpnetEncoder, BgeM3Encoder
from towow.field.projector import SimHashProjector, MrlBqlProjector
from towow.field.pipeline import EncodingPipeline
from towow.field.profile_loader import load_profiles_from_json, profile_to_text, load_all_profiles
from towow.field.multi_perspective import MultiPerspectiveGenerator, MultiPerspectiveResult

__all__ = [
    # Protocol
    "IntentField",
    "Encoder",
    "Projector",
    # Types
    "Intent",
    "FieldResult",
    "OwnerMatch",
    # Implementation
    "MemoryField",
    "MpnetEncoder",
    "BgeM3Encoder",
    "SimHashProjector",
    "MrlBqlProjector",
    "EncodingPipeline",
    # Multi-perspective query
    "MultiPerspectiveGenerator",
    "MultiPerspectiveResult",
    # Profile utilities
    "load_profiles_from_json",
    "profile_to_text",
    "load_all_profiles",
]
