from typing import TypeVar, Tuple, Optional, Any
from sqlalchemy.orm import Query
from sqlalchemy import desc, or_, and_
from base64 import b64encode, b64decode
import json
from datetime import datetime
from fastapi import Query
from simplebank.models.schemas import PaginatedResponse
from simplebank.models.models import Transaction

T = TypeVar('T')

class PaginationField:
    """Configuration for pagination fields"""
    def __init__(self, field_name: str, is_timestamp: bool = False):
        self.field_name = field_name
        self.is_timestamp = is_timestamp

def encode_cursor(values: dict) -> str:
    """
    Encode cursor values into a base64 string
    """
    cursor_str = json.dumps(values, default=str)  # Handle datetime serialization
    return b64encode(cursor_str.encode('utf-8')).decode('utf-8')

def decode_cursor(cursor: str) -> dict:
    """
    Decode cursor string back into values
    """
    try:
        cursor_str = b64decode(cursor.encode('utf-8')).decode('utf-8')
        values = json.loads(cursor_str)
        print(f"Decoded cursor values: {values}")  # Debug print
        return values
    except Exception as e:
        print(f"Error decoding cursor: {e}")  # Debug print
        return {}

def cursor_paginate(
    query: Query,
    cursor: Optional[str],
    limit: int,
    pagination_fields: list[PaginationField] = None
) -> Tuple[list[T], Optional[str]]:
    """
    Implement cursor-based pagination for a SQLAlchemy query.
    """
    if pagination_fields is None:
        pagination_fields = [
            PaginationField("timestamp", is_timestamp=True),
            PaginationField("id")
        ]

    # Apply cursor if provided
    if cursor:
        try:
            cursor_values = decode_cursor(cursor)
            
            timestamp_value = None
            id_value = None
            
            for field in pagination_fields:
                field_value = cursor_values.get(field.field_name)
                if field_value is not None:
                    if field.is_timestamp and isinstance(field_value, str):
                        timestamp_value = datetime.fromisoformat(field_value)
                    elif field.field_name == "id":
                        id_value = field_value

            if timestamp_value and id_value:
                query = query.filter(
                    or_(
                        Transaction.timestamp < timestamp_value,
                        and_(
                            Transaction.timestamp == timestamp_value,
                            Transaction.id < id_value
                        )
                    )
                )
                
        except Exception as e:
            print(f"Error applying cursor pagination: {e}")
            return [], None

    # Get one extra item to determine if there are more results
    items = query.limit(limit + 1).all()
    print(f"Retrieved {len(items)} items")  # Debug print
    
    has_next = len(items) > limit
    items = items[:limit]

    # Generate next cursor if there are more items
    next_cursor = None
    if has_next and items:  # Only generate next_cursor if there are more items
        last_item = items[-1]
        cursor_values = {}
        for field in pagination_fields:
            value = getattr(last_item, field.field_name)
            cursor_values[field.field_name] = value
        next_cursor = encode_cursor(cursor_values)
        print(f"Generated next cursor from values: {cursor_values}")  # Debug print
    else:
        print("No more pages available")  # Debug print

    return items, next_cursor

async def paginate_query(
    query: Query,
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page"),
    pagination_fields: list[PaginationField] = None,
) -> PaginatedResponse:
    """
    Helper function to paginate a query in FastAPI endpoints
    """
    if pagination_fields is None:
        pagination_fields = [
            PaginationField("timestamp", is_timestamp=True),
            PaginationField("id")
        ]
    
    items, next_cursor = cursor_paginate(
        query=query,
        cursor=cursor,
        limit=limit,
        pagination_fields=pagination_fields
    )
    
    return PaginatedResponse(
        items=items,
        next_cursor=next_cursor
    )