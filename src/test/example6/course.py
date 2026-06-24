"""
Course models for example 6.
"""

from person import Staff, Student


class Syllabus:
    def __init__(self, outline: str):
        self.outline = outline


class Course:
    def __init__(self, code: str, instructor: Staff):
        self.code = code
        self.instructor: Staff = instructor
        self.syllabus: Syllabus = Syllabus("default")
        self.students: list[Student] = []

    def enroll(self, student: Student) -> None:
        self.students.append(student)

    def rename(self, code: str) -> None:
        self.code = code

