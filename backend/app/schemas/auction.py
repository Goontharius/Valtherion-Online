from pydantic import BaseModel


class AuctionListingCreate(BaseModel):
    item_id: str
    quantity: int = 1
    unit_price: int
    currency: str = "kupdun"
