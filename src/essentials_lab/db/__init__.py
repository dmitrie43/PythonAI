"""
Реэкспорт ORM-моделей пакета db.

Чтобы можно было: from essentials_lab.db import TicketModel
"""

from essentials_lab.db.models import Base, NoteModel, TicketModel

__all__ = ["Base", "NoteModel", "TicketModel"]
