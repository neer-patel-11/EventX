
from enum import Enum as PyEnum

class EventResult(PyEnum):
    YES='yes'
    NO='no'
    DRAW='draw'

class EventStatus(PyEnum):
    ONGOING='ongoing'
    COMPLETED='completed'
    