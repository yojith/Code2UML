"""
Library models for example 6.
"""

from course import Course
from person import Staff, Student


class LibraryCard:
    def __init__(self, card_number: str):
        self.card_number = card_number


class Library:
    def __init__(self, name: str, librarian: Staff):
        self.name = name
        self.librarian: Staff = librarian
        self.courses: list[Course] = []
        self.cards: list[LibraryCard] = []

    def add_course(self, course: Course) -> None:
        self.courses.append(course)

    def issue_card(self, student: Student) -> None:
        card = LibraryCard(student.display_name())
        self.cards.append(card)

