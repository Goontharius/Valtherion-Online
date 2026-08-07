# Valtherion Online API - Client Integration Guide
# For Unity and Unreal Engine

## API Base URLs

Development: http://localhost:8000
Production: https://api.valtheriononline.com

## Authentication

All authenticated endpoints require a Bearer token:
```
Authorization: Bearer <access_token>
```

Authentication flow:
1. POST /register - Create account (returns access_token + refresh_token)
2. POST /login - Log in (returns access_token + refresh_token)
3. POST /refresh - Refresh expired token

```json
// Refresh request body
POST /refresh
{ "refresh_token": "<refresh_token>" }
```

## WebSocket Connection

```
ws://localhost:8000/ws/{access_token}
```

The WebSocket handles real-time features:
- Chat (general, private, party channels)
- Position synchronization
- Real-time PvP combat
- Party invite responses

## REST API Endpoints

### Player
| Method | Path | Description |
|--------|------|-------------|
| GET | /player/profile | Get full character data |
| GET | /player/inventory | Get inventory, hotbar, equipment |
| POST | /player/move | Move character (3D position) |
| POST | /player/use-skill | Activate a combat skill |
| POST | /player/consume | Use a consumable item |
| POST | /player/allocate-stats | Allocate stat points |

### Inventory
| Method | Path | Description |
|--------|------|-------------|
| GET | /inventory/ | Get full inventory |
| POST | /inventory/equip/{item_id} | Equip an item |
| POST | /inventory/unequip/{slot} | Unequip a slot |
| POST | /inventory/hotbar | Set hotbar slot |

### Guild
| Method | Path | Description |
|--------|------|-------------|
| POST | /guild/create | Create guild (lvl 25 + tribute) |
| GET | /guild/my | Get player's current guild (with member details) |
| GET | /guild/{name} | Get guild info |
| GET | /guild/ | List all guilds |
| POST | /guild/join/{id} | Join a guild (respects member capacity) |
| POST | /guild/leave | Leave current guild (transfers leadership / deletes if empty) |
| POST | /guild/kick/{player_id} | Kick member (leader/officer only) |
| POST | /guild/roles/{player_id} | Set role to officer\|member (leader only) |
| POST | /guild/donate | Donate currency to treasury (`?amount=&currency_type=`); grants likeness (kupdun 1/10, zirdun x10, guldun x1000) |
| GET | /guild/hall | Get guild hall + construction progress |
| POST | /guild/hall/petition | Petition the Local Lord to start a hall (needs 500 likeness) |
| POST | /guild/hall/resources | Donate materials to hall (capped by requirements and your inventory) |
| POST | /guild/hall/start-build | Start construction (leader only, after resources gathered) |
| POST | /guild/hall/feature | Build a hall feature (leader only, hall must be built; costs treasury) |
| GET | /guild/vault | Get guild vault contents |
| POST | /guild/vault/deposit | Deposit item into vault (`?item_id=&quantity=`) |
| POST | /guild/vault/withdraw | Withdraw item from vault (`?item_id=&quantity=`) |
| GET | /guild/missions/{type} | Get available missions by guild type |
| GET | /guild/missions/active | Get active missions |
| GET | /guild/missions/completed | Get completed missions |
| POST | /guild/missions/accept | Accept a mission (leader/officer only; max 3 active) |
| POST | /guild/missions/progress | Progress a mission (`{"mission_id", "amount"}`) |
| POST | /guild/missions/complete | Complete a mission (grants likeness + guild XP/levels) |

### Party
| Method | Path | Description |
|--------|------|-------------|
| POST | /party/create | Create a party (max 15) |
| POST | /party/invite/{username} | Invite player to party |
| POST | /party/join/{party_id} | Join a party directly |
| GET | /party/me | Get current party info (with member details) |
| POST | /party/leave | Leave current party |
| POST | /party/kick/{player_id} | Kick member (leader only) |
| POST | /party/settings | Update party loot/exp settings (leader only; loot_mode: free_for_all\|round_robin, experience_share: bool) |

### Trade
| Method | Path | Description |
|--------|------|-------------|
| POST | /trade/request | Send a trade offer |

### Shop
| Method | Path | Description |
|--------|------|-------------|
| GET | /shop/ | List all merchants |
| GET | /shop/{merchant_id} | Get merchant inventory |
| POST | /shop/buy/{merchant_id}/{item_id} | Buy from merchant |
| POST | /shop/sell/{item_id} | Sell to merchant |

### Dungeons
| Method | Path | Description |
|--------|------|-------------|
| GET | /dungeons/active | List active dungeons |
| GET | /dungeons/{id} | Get dungeon details |
| POST | /dungeons/{id}/enter | Enter dungeon |
| POST | /dungeons/{id}/leave | Leave dungeon |

### Quests
| Method | Path | Description |
|--------|------|-------------|
| GET | /quests/available | List available quests |
| POST | /quests/accept | Accept a quest |
| POST | /quests/progress | Update quest progress |
| POST | /quests/complete | Complete a quest |
| GET | /quests/active | Get active quests |
| GET | /quests/completed | Get completed quests |

### Combat
| Method | Path | Description |
|--------|------|-------------|
| POST | /combat/attack-monster/{id} | Attack a monster (PvE). Defeating a monster auto-progresses the killer's (and party members') active kill quests whose target matches the monster (response includes `quest_tracking` when a quest updated). |
| POST | /combat/attack-player/{target_id} | Attack another player (PvP). Optional `?skill_id=<id>`. Requires same region and alive attacker; consumes skill stamina/mana. A killing blow defeats + auto-respawns the target at spawn and grants the attacker dark alignment. |

### Crafting
| Method | Path | Description |
|--------|------|-------------|
| GET | /crafting/recipes/{job_type} | List available recipes |
| POST | /crafting/craft/{recipe_id} | Craft an item |
| GET | /crafting/levels | Get crafting levels |

### World
| Method | Path | Description |
|--------|------|-------------|
| GET | /world/bosses | World boss status |
| GET | /world/regions | List all regions |
| GET | /world/regions/{name} | Get region details |
| GET | /world/nearby | Get nearby players |
| POST | /world/travel | Travel to a connected region |
| POST | /world/region/{name}/announce | Broadcast a region announcement |

### Game Data
| Method | Path | Description |
|--------|------|-------------|
| GET | /data/species | All species + variants |
| GET | /data/classes | All classes |
| GET | /data/skills | All skills |
| GET | /data/skills/{job_class} | Skills by class |

## WebSocket Message Types

### Client -> Server

```json
// Chat
{"type": "chat", "channel": "general|private|party", "message": "...", "recipient": "username"}

// Position update (3D)
{"type": "position_update", "position": {"x": 0, "y": 0, "z": 0, "yaw": 0}}

// PvP attack
{"type": "combat_attack", "target": "username", "skill_id": "power_strike"}

// Party invite response
{"type": "party_invite_response", "accepted": true, "party_id": 1}

// Channel switch
{"type": "channel_switch", "channel": "general"}

// Ping
{"type": "ping"}
```

### Server -> Client

```json
// Connected
{"type": "connected", "message": "Welcome back, ...", "player_id": 1}

// Chat message
{"type": "chat", "from": "username", "from_id": 1, "channel": "general", "message": "...", "timestamp": "..."}

// Player moved
{"type": "player_moved", "player_id": 1, "player_name": "...", "position": {...}}

// Combat hit (attacker perspective)
{"type": "you_attacked", "attacker": "...", "attacker_id": 1, "target_id": 2, "damage": 15, "critical": false, "damage_type": "physical", "skill_id": "power_strike", "target_hp": 85}

// Combat hit (target perspective)
{"type": "you_were_hit", "attacker": "...", "attacker_id": 1, "target_id": 2, "damage": 15, "critical": false, "damage_type": "physical", "skill_id": "power_strike", "current_hp": 85}

// Combat rejection (self-attack or insufficient stamina/mana)
{"type": "combat_error", "message": "Not enough stamina or mana to use that skill"}

// Combat resolution (killing blow)
{"type": "combat_victory", "target": "...", "target_id": 2, "message": "You defeated your opponent"}
{"type": "combat_defeated", "attacker": "...", "attacker_id": 1, "message": "You were defeated in combat"}

// Party update
{"type": "party_member_joined", "player_id": 1, "player_name": "...", "members": [...]}
```

## Unity Integration Notes

- Use UnityWebRequest or HttpClient for REST calls
- Use NativeWebSocket or BestHTTP for WebSocket
- Store access_token in PlayerPrefs or persistent storage
- Implement auto-refresh on 401 responses
- Send position updates at 10-30 Hz via WebSocket
- Interpolate other players' positions between updates

## Unreal Engine Integration Notes

- Use HttpModule or VaRest plugin for REST calls
- Use WebSockets module for real-time communication
- Store tokens in SaveGame objects
- Use Gameplay Ability System (GAS) for skills
- Use replication for 3D position sync in single-instance mode
- For MMO-style, use the WebSocket-based position sync

## Currency System

- Kupdun (Tier 1) - Common currency
- Zirdun (Tier 2) - 100 Kupdun
- Guldun (Tier 3) - 10,000 Kupdun

## Item Rarity Tiers

- Common (White)
- Uncommon (Green)
- Rare (Blue)
- Epic (Purple)
- Legendary (Orange)
- God-Tier (Red)
