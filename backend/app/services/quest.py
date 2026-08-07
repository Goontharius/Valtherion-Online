from typing import Optional, List, Dict, Any
from app.services.game_data import QUEST_DATA


def get_available_quests(player_level: int, player_region: str, guilds: List[str] = None) -> List[Dict[str, Any]]:
    available = []
    for quest in QUEST_DATA:
        if quest["min_level"] > player_level:
            continue
        if quest.get("region") and quest["region"] != player_region:
            continue
        available.append(quest)
    return available


def get_quest_by_id(quest_id: int) -> Optional[Dict[str, Any]]:
    for quest in QUEST_DATA:
        if quest["id"] == quest_id:
            return quest
    return None


def can_accept_quest(quest: Dict[str, Any], player_level: int, active_quests: List[Dict], completed_quests: List[int]) -> tuple[bool, str]:
    if quest["min_level"] > player_level:
        return False, f"Requires level {quest['min_level']}"
    for aq in active_quests:
        if aq.get("quest_id") == quest["id"]:
            return False, "Quest already active"
    if quest["id"] in completed_quests and not quest.get("is_repeatable", False):
        return False, "Quest already completed"
    return True, ""


def update_quest_progress(active_quests: List[Dict], quest_id: int, objective_index: int, amount: int = 1) -> List[Dict]:
    for quest in active_quests:
        if quest.get("quest_id") == quest_id:
            progress = quest.get("progress", [])
            while len(progress) <= objective_index:
                progress.append({"current": 0, "required": 0})

            objectives = quest.get("objectives", [])
            if objective_index < len(objectives):
                progress[objective_index]["current"] += amount
                progress[objective_index]["required"] = objectives[objective_index].get("count", 1)

            quest["progress"] = progress
            break
    return active_quests


def apply_kill_tracking(active_quests: List[Dict], monster_name: str, amount: int = 1) -> tuple[List[Dict], bool]:
    """Auto-increment progress for active kill quests whose target matches the
    monster that was just defeated. Progress is capped at the objective's
    required count. Returns the (possibly mutated) active quests plus a flag
    indicating whether any quest changed.
    """
    changed = False
    for quest in active_quests:
        objectives = quest.get("objectives", [])
        progress = quest.get("progress", [])
        for i, obj in enumerate(objectives):
            if obj.get("type") != "kill":
                continue
            if obj.get("target") != monster_name:
                continue
            while len(progress) <= i:
                progress.append({"current": 0, "required": obj.get("count", 1)})
            required = obj.get("count", progress[i].get("required", 1))
            current = min(required, progress[i].get("current", 0) + amount)
            if current != progress[i].get("current", 0):
                progress[i]["current"] = current
                progress[i]["required"] = required
                changed = True
    return active_quests, changed


def is_quest_complete(quest_entry: Dict) -> bool:
    progress = quest_entry.get("progress", [])
    for p in progress:
        if p.get("current", 0) < p.get("required", 1):
            return False
    return True


def get_quest_rewards(quest_id: int) -> Optional[Dict[str, Any]]:
    quest = get_quest_by_id(quest_id)
    if not quest:
        return None
    return quest.get("rewards", {})
