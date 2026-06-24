"""
Person hierarchy for example 6.
"""


class Person:
    def __init__(self, person_id: int, full_name: str):
        self.person_id = person_id
        self.full_name = full_name

    def display_name(self) -> str:
        return self.full_name


class Staff(Person):
    def __init__(self, person_id: int, full_name: str, title: str):
        super().__init__(person_id, full_name)
        self.title = title


class Student(Person):
    def __init__(self, person_id: int, full_name: str, major: str):
        super().__init__(person_id, full_name)
        self.major = major

