# Valtherion Online - GDD Summary

This document captures the core design and systems from the extracted Valtherion Online 4.0 game design document. It also maps the current project implementation to those systems.

## Core Gameplay Systems

### Introduction / World
- Valtherion is a medieval fantasy MMO-style world threatened by the Dark Demon Lord Zorvathax.
- Regions include Shadowfen, Emberfield, Frostmead, Stormcrest, Wraithmoor, and more.
- The design includes cinematic introduction, save/load flow, and in-game UI immersion.

### Main Menu and UI
- Main menu options: Save, Load, Profile, Inventory, Quests, Settings, Party, Guild, Trade, Exit.
- The app uses a dark stone and runic aesthetic with guild emblems and immersive background visuals.
- The existing mobile app contains placeholder screens for these sections and a working navigation structure.

### Player and Profile Systems
- Player profile includes stats, job-class levels, experience, current HP/Mana/Stamina, hunger, currency, guild rank, and achievements.
- New players start in Murkfen Hamlet with tutorial onboarding.
- The backend already supports player registration, login, and profile retrieval.

### Inventory and Item Systems
- Inventory is a 10x5 grid with stackable materials and unique gear.
- Items can be equipped, consumed, traded, or used in crafting.
- Excess loot may be discarded, traded, or stored in a guild vault.
- The backend currently returns player inventory and supports consuming items and buying items from merchant shops.

### Chat and Messaging
- Player-to-player instant messaging and party messaging are defined by the GDD.
- Guild-specific messaging channels are planned.
- The mobile client now includes a `ChatScreen` and websocket support for real-time messages.

### Party and Guild Systems
- Parties can form with up to 15 members, share loot and experience, and include emblem customization.
- Guilds require level 25+ and a tribute payment to form.
- Guild formation includes petitions, emblems, likeness with local lords, and guild halls.
- The backend supports party create/invite/join/leave/kick, per-party loot mode (free_for_all or round_robin) and experience sharing settings, and guild creation endpoints, matching the GDD foundation.
- Party combat distributes experience to all members when sharing is enabled and splits loot by the configured mode (round_robin splits Common drops evenly with remainder to the killer and rolls rare+ tiers; free_for_all gives everything to the killer).
- Guilds are deep: create (level 25 + tribute), join (respects member capacity), leave (with leadership transfer / guild deletion), kick and role management (leader/officer), treasury donations with likeness gains, hall petition → resource gathering → construction → features, a shared vault (deposit/withdraw with capacity), and mission accept/progress/complete with expiry and guild XP/leveling that grows member capacity. Hall resource donations are capped by both hall requirements and the donating player's actual inventory.

### Combat, Skills, and Quests
- The GDD defines class-specific skill systems and quest difficulty scaling.
- Skill use, movement, combat, and quest tracking are part of the backend core.
- The backend supports movement, skill use, and quest-related endpoints (available/accept/progress/complete/active/completed), while the mobile screens have placeholders for UI.
- Merchant shops support buy and sell flows across multiple currencies (Kupdun/Zirdun/Guldun).
- Crafting supports per-job recipe listings, material validation/consumption, success/failure, and crafted item awards.
- Dungeons support active listings, details, enter, and leave.
- Player actions include movement (position/direction/sprint/rotation), skill use with stamina/mana costs and cooldowns, consumables with vital/stat effects, and stat-point allocation that recomputes max vitals.
- Inventory supports equipping/unequipping into slots with swap-back behavior and hotbar binding.
- The game-data endpoints expose species, classes, and skills; world endpoints include region announce.
- Quest kill objectives are automated: defeating a monster in combat automatically increments progress on the killer's (and party members') active kill quests whose target matches the defeated monster, capped at the objective count.

### Player vs. Player (PvP) Combat
- The GDD defines opt-in, consent-based PvP with wagers, arenas, and cooldowns. The backend provides a foundation for this: a REST attack endpoint and WebSocket real-time PvP.
- REST: `POST /combat/attack-player/{target_id}?skill_id=<id>` performs a single attack, consuming the skill's stamina/mana cost, honoring region proximity and alive checks, setting combat states, and applying damage against the target's defense (constitution + equipped armor).
- On a killing blow the target is defeated and auto-respawns at Murkfen Hamlet at full vitals (no corpse loot/EXP loss, matching duel rules), while the attacker gains dark alignment points.
- WebSocket: `combat_attack` messages apply the same damage/cost/defeat rules and push `you_attacked` / `you_were_hit` / `combat_victory` / `combat_defeated` / `combat_error` events to the involved clients.
- Not yet implemented: wager matching, arena selection, mutual consent flow, and the 1-hour post-match cooldown.

## Deployment and Project Integration

### Backend Enhancements
- Environment variables are now supported through `.env` and `dotenv`.
- Database tables are auto-created on startup to simplify deployment.
- A `Dockerfile` and `docker-compose.yml` are provided for backend, database, and Redis deployment.

### Documentation
- The full extracted GDD text is stored in `docs/Valtherion Online 4.0 GDD.txt`.
- This summary is available at `docs/GDD_SUMMARY.md`.

### What is implemented
- Backend: authentication, player profile, inventory, movement, skill use, consumables, trade, party, guild, shop, combat (PvE + PvP), crafting, quests, dungeons, world, game data, websocket chat/positions/PvP/party.
- Mobile: login, registration, game home, profile, full inventory UI (item grid, equipment, hotbar, equip/consume/sell), party UI (create/invite/kick/leave), guild UI (create/join/browse/missions/leave), quests UI (available/active/completed), chat screen with websocket, shop stub, settings stub.
- The mobile Inventory, Party, Guild, and Quests screens are now fully wired to the backend API.

## Next Improvements
- Add the Shop UI and full buying/selling flows.
- Add the Settings UI.
- Implement party emblems and guild hall/likeness management UI.
- Add full chat channel support for guild/party/private messaging.
- Expand the backend to support saved party emblems.
- Implement quest and mission flows based on the GDD details.
- Add dungeon boss/reward encounters and further objective automation (e.g. collect/deliver tracking wired to inventory actions).
- Deepen PvP: wager matching, arena selection, mutual consent, and post-match cooldown.
- Add auction edge-case coverage (invalid listings, filters) and websocket edge-case tests.
