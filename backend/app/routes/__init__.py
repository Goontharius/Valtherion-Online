from app.routes.auth import router as auth_router
from app.routes.player import router as player_router
from app.routes.inventory import router as inventory_router
from app.routes.party import router as party_router
from app.routes.guild import router as guild_router
from app.routes.trade import router as trade_router
from app.routes.shop import router as shop_router
from app.routes.auction import router as auction_router
from app.routes.dungeon import router as dungeon_router
from app.routes.quest import router as quest_router
from app.routes.combat import router as combat_router
from app.routes.crafting import router as crafting_router
from app.routes.world import router as world_router
from app.routes.data import router as data_router
from app.routes.friends import router as friends_router
from app.routes.bank import router as bank_router

routes = [
    auth_router,
    player_router,
    inventory_router,
    party_router,
    guild_router,
    trade_router,
    shop_router,
    auction_router,
    dungeon_router,
    quest_router,
    combat_router,
    crafting_router,
    world_router,
    data_router,
    friends_router,
    bank_router,
]
