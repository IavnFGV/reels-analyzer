from dataclasses import dataclass


@dataclass(slots=True)
class SourceVideoLink:
    url: str
    channel_name: str
