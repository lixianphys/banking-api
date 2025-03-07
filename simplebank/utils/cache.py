from fastapi import Request, Response
from datetime import datetime
from pydantic import BaseModel

from simplebank.utils.security_deps import SecurityAudit
import json
import hashlib
from typing import Any



# Custom JSON encoder to handle datetime objects and Pydantic models
class APIJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, BaseModel):
            return obj.model_dump()  # For Pydantic v2
        return super().default(obj)

    

def generate_etag(data: Any) -> str:
    """Generate ETag from response data"""
    # Convert data to a consistent string representation
    if hasattr(data, "model_dump"):  # For Pydantic v2
        # Handle Pydantic models with datetime-safe serialization
        data_dict = data.model_dump()
        data_str = json.dumps(data_dict, sort_keys=True, cls=APIJSONEncoder)
    elif hasattr(data, "dict"):  # For Pydantic v1
        # Handle Pydantic models with datetime-safe serialization
        data_dict = data.dict()
        data_str = json.dumps(data_dict, sort_keys=True, cls=APIJSONEncoder)
    elif isinstance(data, (dict, list)):
        # Handle dictionaries and lists with datetime-safe serialization
        data_str = json.dumps(data, sort_keys=True, cls=APIJSONEncoder)
    else:
        # Handle other types
        data_str = str(data)
    
    # Generate hash
    return hashlib.md5(data_str.encode()).hexdigest()

def check_conditional_request(request: Request, response: Response, data: Any):
    """Check if we can return 304 Not Modified"""
    etag = generate_etag(data)
    response.headers["ETag"] = etag
    
    # Check If-None-Match header
    if_none_match = request.headers.get("If-None-Match")
    if if_none_match and if_none_match == etag:
        response.status_code = 304
        return True
    
    return False
