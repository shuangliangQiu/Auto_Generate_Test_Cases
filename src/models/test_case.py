# src/models/test_case.py
from typing import List
from dataclasses import dataclass
import uuid

@dataclass
class TestCase:
    """Model representing a test case."""
    
    title: str
    description: str
    preconditions: List[str]
    steps: List[str]
    expected_results: List[str]
    priority: str
    category: str
    
    def __post_init__(self):
        self.id = str(uuid.uuid4())
        self.status = "Draft"
        self.created_at = None
        self.updated_at = None
        self.created_by = None
        self.last_updated_by = None
        
    def to_dict(self) -> dict:
        """Convert test case to dictionary format."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'preconditions': self.preconditions,
            'steps': self.steps,
            'expected_results': self.expected_results,
            'priority': self.priority,
            'category': self.category,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'created_by': self.created_by,
            'last_updated_by': self.last_updated_by
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TestCase':
        """Create test case from dictionary."""
        instance = cls(
            title=data['title'],
            description=data['description'],
            preconditions=data['preconditions'],
            steps=data['steps'],
            expected_results=data['expected_results'],
            priority=data['priority'],
            category=data['category']
        )
        
        # Set additional attributes
        instance.id = data.get('id', instance.id)
        instance.status = data.get('status', instance.status)
        instance.created_at = data.get('created_at')
        instance.updated_at = data.get('updated_at')
        instance.created_by = data.get('created_by')
        instance.last_updated_by = data.get('last_updated_by')
        
        return instance