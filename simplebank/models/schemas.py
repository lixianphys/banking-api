from pydantic import BaseModel, ConfigDict

# Customer schemas
class CustomerBase(BaseModel):
    name: str

class CustomerCreate(CustomerBase):
    pass

class Customer(CustomerBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

