import { configureStore } from '@reduxjs/toolkit';
import playerReducer from './playerSlice';
import chatReducer from './chatSlice';
import partyReducer from './partySlice';

export const store = configureStore({
  reducer: {
    player: playerReducer,
    chat: chatReducer,
    party: partyReducer,
  },
});
