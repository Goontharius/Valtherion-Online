from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone
from app.core.database import Base


class AuctionListing(Base):
    __tablename__ = "auction_listings"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, index=True, nullable=False)
    seller_name = Column(String(50))
    item_id = Column(String(100), index=True)
    item_name = Column(String(100))
    item_type = Column(String(50), default="material")
    item_rarity = Column(String(50), default="Common")
    quantity = Column(Integer, default=1)
    unit_price = Column(Integer, default=1)
    currency = Column(String(20), default="kupdun")
    status = Column(String(20), default="active", index=True)
    buyer_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)
    sold_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "seller_id": self.seller_id,
            "seller_name": self.seller_name,
            "item_id": self.item_id,
            "item_name": self.item_name,
            "item_type": self.item_type,
            "item_rarity": self.item_rarity,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total_price": (self.unit_price or 0) * (self.quantity or 1),
            "currency": self.currency,
            "status": self.status,
            "buyer_id": self.buyer_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "sold_at": self.sold_at.isoformat() if self.sold_at else None,
        }
