from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PartSummary(CamelModel):
    index: int
    duration: float
    start: float
    end: float


class RecordingSummary(CamelModel):
    id: str
    title: str
    part_count: int
    total_duration: float


class RecordingDetail(CamelModel):
    id: str
    title: str
    parts: list[PartSummary]
    total_duration: float


class Word(CamelModel):
    word: str
    start: float
    end: float
    part: int


class MergedTranscript(CamelModel):
    recording_id: str
    total_duration: float
    parts: list[PartSummary]
    words: list[Word]
