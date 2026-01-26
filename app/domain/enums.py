import enum


class ProductImportance(str, enum.Enum):
    NECESSARY = "necessary"
    IMPORTANT = "important"
    UNNECESSARY = "unnecessary"
