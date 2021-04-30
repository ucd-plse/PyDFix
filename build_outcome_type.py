from enum import IntEnum


class BuildOutcomeType(IntEnum):
    BUILD_SUCCESSFUL = 1
    SAME_ERROR = 2
    NEW_ERROR = 3