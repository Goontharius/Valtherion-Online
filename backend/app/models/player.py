from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text, ForeignKey
from datetime import datetime, timezone
from app.core.database import Base
from app.core.json_types import MutableJSON, MutableJSONArray


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(200))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    level = Column(Integer, default=1)
    experience = Column(Integer, default=0)
    stat_points = Column(Integer, default=50)

    species = Column(String(50), default="Human")
    species_variant = Column(String(50), default="Base")
    alignment_points = Column(MutableJSON(), default=lambda: {"light": 0, "dark": 0})

    strength = Column(Integer, default=10)
    dexterity = Column(Integer, default=10)
    intelligence = Column(Integer, default=10)
    wisdom = Column(Integer, default=10)
    constitution = Column(Integer, default=10)
    charisma = Column(Integer, default=10)

    luck = Column(Integer, default=0)
    luck_unlocked = Column(Boolean, default=False)

    current_hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)
    current_mana = Column(Integer, default=50)
    max_mana = Column(Integer, default=50)
    current_stamina = Column(Integer, default=100)
    max_stamina = Column(Integer, default=100)
    hunger = Column(Integer, default=100)

    current_region = Column(String(100), default="Murkfen Hamlet")
    position_x = Column(Float, default=0)
    position_y = Column(Float, default=0)
    position_z = Column(Float, default=0)
    rotation_yaw = Column(Float, default=0)

    inventory = Column(MutableJSONArray(), default=list)
    hotbar = Column(MutableJSONArray(), default=list)
    equipment = Column(MutableJSON(), default=dict)

    currency = Column(MutableJSON(), default=lambda: {"kupdun": 100, "zirdun": 0, "guldun": 0})

    job_class = Column(String(50), default="Warrior")
    job_level = Column(Integer, default=1)
    sub_class = Column(String(50), nullable=True)
    main_class = Column(String(50), nullable=True)

    crafting_levels = Column(MutableJSON(), default=lambda: {
        "blacksmithing": 1, "alchemy": 1, "enchanting": 1,
        "fletching": 1, "leatherworking": 1, "cooking": 1,
    })

    guilds = Column(MutableJSONArray(), default=list)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True)

    active_quests = Column(MutableJSONArray(), default=list)
    completed_quests = Column(MutableJSONArray(), default=list)

    skills = Column(MutableJSONArray(), default=list)
    known_recipes = Column(MutableJSONArray(), default=list)

    friends = Column(MutableJSONArray(), default=list)
    ignored_players = Column(MutableJSONArray(), default=list)

    status_effects = Column(MutableJSONArray(), default=list)
    combat_state = Column(String(20), default="idle")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "level": self.level,
            "experience": self.experience,
            "stat_points": self.stat_points,
            "species": self.species,
            "species_variant": self.species_variant,
            "alignment_points": self.alignment_points,
            "job_class": self.job_class,
            "job_level": self.job_level,
            "sub_class": self.sub_class,
            "main_class": self.main_class,
            "crafting_levels": self.crafting_levels,
            "stats": {
                "strength": self.strength,
                "dexterity": self.dexterity,
                "intelligence": self.intelligence,
                "wisdom": self.wisdom,
                "constitution": self.constitution,
                "charisma": self.charisma,
                "luck": self.luck if self.luck_unlocked else None,
            },
            "vitals": {
                "current_hp": self.current_hp,
                "max_hp": self.max_hp,
                "current_mana": self.current_mana,
                "max_mana": self.max_mana,
                "current_stamina": self.current_stamina,
                "max_stamina": self.max_stamina,
                "hunger": self.hunger,
            },
            "position": {
                "region": self.current_region,
                "x": self.position_x,
                "y": self.position_y,
                "z": self.position_z,
                "yaw": self.rotation_yaw,
            },
            "currency": self.currency,
            "guilds": self.guilds,
            "party_id": self.party_id,
            "skills": self.skills,
            "equipment": self.equipment,
            "status_effects": self.status_effects,
            "combat_state": self.combat_state,
        }

    def get_racial_traits(self) -> dict:
        traits = {
            "Human": {
                "stat_bonus": {"any": 2},
                "passive": "Jack of All Trades",
                "passive_effect": "10% experience bonus",
            },
            "Elf": {
                "stat_bonus": {"dexterity": 3, "intelligence": 2},
                "passive": "Forest Whisper",
                "passive_effect": "+2 stealth, +10% movement speed in forests",
            },
            "Dwarf": {
                "stat_bonus": {"constitution": 3, "strength": 2},
                "passive": "Stonekin",
                "passive_effect": "+2 armor, 20% knockback resistance",
            },
            "Orc": {
                "stat_bonus": {"strength": 3, "constitution": 2},
                "passive": "Bloodrage",
                "passive_effect": "+10% damage below 30% HP, +5% attack speed for 10s after kill",
            },
            "Gnome": {
                "stat_bonus": {"intelligence": 3, "dexterity": 2},
                "passive": "Tinker's Wit",
                "passive_effect": "+10% crafting speed, 5% material recovery on failed craft",
            },
        }
        return traits.get(self.species, traits["Human"])

    def get_variant_traits(self) -> dict:
        variants = {
            "Human": {
                "Lightborne": {
                    "stat_bonus": {"wisdom": 3, "charisma": 2},
                    "passive": "Beacon of Hope",
                    "passive_effect": "Allies within 10m gain +5% damage resistance, +10% healing received",
                },
                "Shadowkin": {
                    "stat_bonus": {"intelligence": 3, "dexterity": 2},
                    "passive": "Veil of Shadows",
                    "passive_effect": "+10% crit chance in low-light, +5% damage vs Light enemies",
                },
            },
            "Elf": {
                "Lumina": {
                    "stat_bonus": {"intelligence": 3, "wisdom": 2},
                    "passive": "Starlit Grace",
                    "passive_effect": "+10% mana regen, +5% healing in forests",
                },
                "Duskborn": {
                    "stat_bonus": {"dexterity": 3, "intelligence": 2},
                    "passive": "Night's Embrace",
                    "passive_effect": "+10% spell damage at night, +5% evasion in shadows",
                },
            },
            "Dwarf": {
                "Forgelight": {
                    "stat_bonus": {"constitution": 3, "wisdom": 2},
                    "passive": "Forgefather's Ward",
                    "passive_effect": "+3 armor, +10% damage resistance below 50% HP",
                },
                "Deepshadow": {
                    "stat_bonus": {"strength": 3, "constitution": 2},
                    "passive": "Cavern's Might",
                    "passive_effect": "+10% melee damage underground, +5% crit vs stunned foes",
                },
            },
            "Orc": {
                "Sunfury": {
                    "stat_bonus": {"strength": 3, "charisma": 2},
                    "passive": "Solar Wrath",
                    "passive_effect": "+10% damage vs Dark enemies, +5% HP regen in daylight",
                },
                "Nightrend": {
                    "stat_bonus": {"strength": 3, "dexterity": 2},
                    "passive": "Bloodthirst",
                    "passive_effect": "+15% damage below 30% HP, heal 5% HP on critical hits",
                },
            },
            "Gnome": {
                "Brightspark": {
                    "stat_bonus": {"intelligence": 3, "wisdom": 2},
                    "passive": "Luminous Craft",
                    "passive_effect": "+15% crafting speed, +5% spell damage with crafted weapons",
                },
                "Gloomgear": {
                    "stat_bonus": {"intelligence": 3, "dexterity": 2},
                    "passive": "Dark Ingenuity",
                    "passive_effect": "+10% damage with crafted weapons, +5% speed when stealthed",
                },
            },
        }
        return variants.get(self.species, {}).get(self.species_variant, {})
