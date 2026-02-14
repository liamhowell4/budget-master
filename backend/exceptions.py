"""Custom exception types for the finance_bot backend."""


class DocumentNotFoundError(Exception):
    """Raised when a Firestore document is not found."""

    def __init__(self, collection: str, document_id: str):
        self.collection = collection
        self.document_id = document_id
        super().__init__(f"{collection} document '{document_id}' not found")


class InvalidCategoryError(ValueError):
    """Raised when an invalid expense category is provided."""

    def __init__(self, category_id: str):
        self.category_id = category_id
        super().__init__(f"Invalid category '{category_id}'")
