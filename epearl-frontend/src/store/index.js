import { configureStore } from '@reduxjs/toolkit';
import authReducer from '../features/auth/store/authSlice';
import exploreReducer from '../features/explore/store/exploreSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    explore: exploreReducer,
  },
});