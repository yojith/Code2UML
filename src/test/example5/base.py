"""
Base domain entities for example 5.
"""


class Identified:
    def __init__(self, identifier: int):
        self.identifier = identifier


class Timestamped:
    def __init__(self):
        self.created_at = None
        self.updated_at = None

