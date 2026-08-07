import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  id: null,
  name: '',
  leader_id: null,
  members: [],
  emblem: {},
};

const partySlice = createSlice({
  name: 'party',
  initialState,
  reducers: {
    setParty: (state, action) => ({ ...state, ...action.payload }),
    clearParty: () => initialState,
    addMember: (state, action) => {
      if (!state.members.includes(action.payload)) {
        state.members.push(action.payload);
      }
    },
    removeMember: (state, action) => {
      state.members = state.members.filter((id) => id !== action.payload);
    },
  },
});

export const { setParty, clearParty, addMember, removeMember } = partySlice.actions;
export default partySlice.reducer;
