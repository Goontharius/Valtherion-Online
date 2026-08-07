import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  isAuthenticated: false,
  id: null,
  username: '',
  level: 1,
  experience: 0,
  species: 'Human',
  speciesVariant: 'Base',
  jobClass: 'Warrior',
  jobLevel: 1,
  mainClass: null,
  subClass: null,
  strength: 10,
  dexterity: 10,
  intelligence: 10,
  wisdom: 10,
  constitution: 10,
  charisma: 10,
  luck: null,
  current_hp: 100,
  max_hp: 100,
  current_mana: 50,
  max_mana: 50,
  current_stamina: 100,
  max_stamina: 100,
  hunger: 100,
  region: 'Murkfen Hamlet',
  position_x: 0,
  position_y: 0,
  currency: {
    kupdun: 100,
    zirdun: 0,
    guldun: 0,
  },
  guilds: [],
  party_id: null,
  active_quests: [],
  completed_quests: [],
  skills: [],
};

const playerSlice = createSlice({
  name: 'player',
  initialState,
  reducers: {
    setPlayer: (state, action) => {
      return { ...state, ...action.payload };
    },
    updatePosition: (state, action) => {
      state.position_x = action.payload.x;
      state.position_y = action.payload.y;
      if (action.payload.region) {
        state.region = action.payload.region;
      }
    },
    updateStats: (state, action) => {
      if (action.payload.current_hp !== undefined) state.current_hp = action.payload.current_hp;
      if (action.payload.current_mana !== undefined) state.current_mana = action.payload.current_mana;
      if (action.payload.current_stamina !== undefined) state.current_stamina = action.payload.current_stamina;
      if (action.payload.hunger !== undefined) state.hunger = action.payload.hunger;
      if (action.payload.experience !== undefined) state.experience = action.payload.experience;
      if (action.payload.level !== undefined) state.level = action.payload.level;
    },
    updateCurrency: (state, action) => {
      state.currency = { ...state.currency, ...action.payload };
    },
    addQuest: (state, action) => {
      state.active_quests.push(action.payload);
    },
    completeQuest: (state, action) => {
      const questId = action.payload;
      const questIndex = state.active_quests.findIndex((q) => q.id === questId);
      if (questIndex !== -1) {
        const [completedQuest] = state.active_quests.splice(questIndex, 1);
        state.completed_quests.push(completedQuest);
      }
    },
    updateSkills: (state, action) => {
      state.skills = action.payload;
    },
    joinParty: (state, action) => {
      state.party_id = action.payload;
    },
    leaveParty: (state) => {
      state.party_id = null;
    },
    joinGuild: (state, action) => {
      state.guilds.push(action.payload);
    },
    leaveGuild: (state, action) => {
      const guildId = action.payload;
      state.guilds = state.guilds.filter((g) => g.id !== guildId);
    },
    setAuthenticated: (state, action) => {
      state.isAuthenticated = action.payload;
    },
    logout: () => initialState,
  },
});

export const {
  setPlayer,
  updatePosition,
  updateStats,
  updateCurrency,
  addQuest,
  completeQuest,
  updateSkills,
  joinParty,
  leaveParty,
  joinGuild,
  leaveGuild,
  setAuthenticated,
  logout,
} = playerSlice.actions;

export default playerSlice.reducer;
