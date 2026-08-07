async def test_data_species_listed(client):
    r = await client.get("/data/species")
    assert r.status_code == 200
    species = r.json()
    names = {s["name"] for s in species}
    assert {"Human", "Elf", "Dwarf", "Orc", "Gnome"} <= names
    human = next(s for s in species if s["name"] == "Human")
    assert "stat_bonuses" in human
    assert "passive" in human
    assert "variants" in human


async def test_data_classes_listed(client):
    r = await client.get("/data/classes")
    assert r.status_code == 200
    classes = r.json()
    names = {c["name"] for c in classes}
    assert {"Warrior", "Mage", "Rogue", "Cleric", "Ranger"} <= names
    warrior = next(c for c in classes if c["name"] == "Warrior")
    assert "power_strike" in warrior["base_skills"]
    assert warrior["base_hp"] > 0
    assert warrior["base_mana"] >= 0


async def test_data_skills_listed(client):
    r = await client.get("/data/skills")
    assert r.status_code == 200
    skills = r.json()
    ids = {s["id"] for s in skills}
    assert "power_strike" in ids
    assert "magic_bolt" in ids
    power = next(s for s in skills if s["id"] == "power_strike")
    assert power["class"] == "Warrior"
    assert power["min_level"] == 1
    assert power["cooldown"] > 0


async def test_data_class_skills_filtered(client):
    r = await client.get("/data/skills/Warrior")
    assert r.status_code == 200
    skills = r.json()
    assert skills
    ids = {s["id"] for s in skills}
    assert "power_strike" in ids
    assert "magic_bolt" not in ids
    assert all("id" in s and "cooldown" in s for s in skills)


async def test_data_class_skills_empty_for_unknown(client):
    r = await client.get("/data/skills/Pirate")
    assert r.status_code == 200
    assert r.json() == []
