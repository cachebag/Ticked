CHECK_MARK = "*"
CROSS_MARK = " "
BULLET = ">"
CURSOR = "_"
ACTIVE_DOT = "●"

from enum import Enum

class MenuState(Enum):
    MAIN = 1
    SEMESTER = 2
    WEEK = 3
    DAY = 4
    ASSIGNMENTS = 5

STARTUP_MESSAGES = [
    "ROBCO INDUSTRIES UNIFIED OPERATING SYSTEM v1.0",
    "COPYRIGHT 2024-2025 ROBCO INDUSTRIES",
    "LOADER V1.1",
    "EXEC VERSION 41.10",
    "-SERVER 1-"
]

SHUTDOWN_MESSAGES = [
    "SHUTTING DOWN ROBCO TERMINAL",
    "SAVING SESSION DATA...",
    "CLEARING MEMORY...",
    "GOODBYE."
]

DAYS_OF_WEEK = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
