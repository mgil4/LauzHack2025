from typing import TypedDict

class VLMState(TypedDict):
    description: str
    video_path: str
    person: bool
    family: bool
    classification: str