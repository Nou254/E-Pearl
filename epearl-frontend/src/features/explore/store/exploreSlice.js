import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { exploreApi } from '../../../api/endpoints/explore';

// Async thunks
export const fetchVenues = createAsyncThunk(
  'explore/fetchVenues',
  async (params, { rejectWithValue }) => {
    try {
      const response = await exploreApi.getVenues(params);
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

export const fetchVenueDetail = createAsyncThunk(
  'explore/fetchVenueDetail',
  async (id, { rejectWithValue }) => {
    try {
      const response = await exploreApi.getVenueDetail(id);
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

export const fetchPublicMenu = createAsyncThunk(
  'explore/fetchPublicMenu',
  async (venueId, { rejectWithValue }) => {
    try {
      const response = await exploreApi.getPublicMenu(venueId);
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

export const fetchEvents = createAsyncThunk(
  'explore/fetchEvents',
  async (venueId, { rejectWithValue }) => {
    try {
      const response = await exploreApi.getEvents(venueId);
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

const initialState = {
  venues: [],
  selectedVenue: null,
  publicMenu: [],
  events: [],
  filters: {
    search: '',
    openNow: false,
    orderBy: '-created_at',
    limit: 20,
  },
  loading: false,
  error: null,
};

const exploreSlice = createSlice({
  name: 'explore',
  initialState,
  reducers: {
    setFilters: (state, action) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearSelectedVenue: (state) => {
      state.selectedVenue = null;
      state.publicMenu = [];
      state.events = [];
    },
  },
  extraReducers: (builder) => {
    builder
      // fetchVenues
      .addCase(fetchVenues.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchVenues.fulfilled, (state, action) => {
        state.loading = false;
        state.venues = action.payload;
      })
      .addCase(fetchVenues.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      // fetchVenueDetail
      .addCase(fetchVenueDetail.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchVenueDetail.fulfilled, (state, action) => {
        state.loading = false;
        state.selectedVenue = action.payload;
      })
      .addCase(fetchVenueDetail.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      // fetchPublicMenu
      .addCase(fetchPublicMenu.fulfilled, (state, action) => {
        state.publicMenu = action.payload;
      })
      .addCase(fetchPublicMenu.rejected, (state, action) => {
        state.error = action.payload;
      })
      // fetchEvents
      .addCase(fetchEvents.fulfilled, (state, action) => {
        state.events = action.payload;
      })
      .addCase(fetchEvents.rejected, (state, action) => {
        state.error = action.payload;
      });
  },
});

export const { setFilters, clearSelectedVenue } = exploreSlice.actions;
export default exploreSlice.reducer;