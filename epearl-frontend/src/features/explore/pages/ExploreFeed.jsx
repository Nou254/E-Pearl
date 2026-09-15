import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchVenues, setFilters } from '../store/exploreSlice';
import VenueCard from '../components/VenueCard';
import SearchBar from '../components/SearchBar';
import FilterBar from '../components/FilterBar';

const ExploreFeed = () => {
  const dispatch = useDispatch();
  const { venues, loading, error, filters } = useSelector((state) => state.explore);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    dispatch(fetchVenues(filters));
  }, [dispatch, filters]);

  const handleSearch = (e) => {
    e.preventDefault();
    dispatch(setFilters({ search: searchTerm }));
  };

  const handleFilterChange = (newFilters) => {
    dispatch(setFilters(newFilters));
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800">Discover Venues</h1>
        <p className="text-gray-600">Find the best restaurants, bars, and hotels near you.</p>
      </div>

      <SearchBar
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        onSearch={handleSearch}
      />
      <FilterBar onFilterChange={handleFilterChange} />

      {loading && <div className="text-center py-8">Loading venues...</div>}
      {error && <div className="text-red-500 text-center py-8">Error: {error}</div>}

      {!loading && !error && venues.length === 0 && (
        <div className="text-center py-8 text-gray-500">No venues found.</div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mt-6">
        {venues.map((venue) => (
          <VenueCard key={venue.id} venue={venue} />
        ))}
      </div>
    </div>
  );
};

export default ExploreFeed;