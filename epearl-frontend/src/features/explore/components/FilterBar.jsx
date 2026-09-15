import React from 'react';

const FilterBar = ({ onFilterChange }) => {
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    const newValue = type === 'checkbox' ? checked : value;
    onFilterChange({ [name]: newValue });
  };

  return (
    <div className="flex flex-wrap items-center gap-4 mb-4 p-4 bg-white rounded-lg shadow">
      <select
        name="orderBy"
        onChange={handleChange}
        className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="-created_at">Newest</option>
        <option value="business_name">Name A-Z</option>
        <option value="-business_name">Name Z-A</option>
      </select>
      <label className="flex items-center gap-2 text-sm text-gray-700">
        <input
          type="checkbox"
          name="openNow"
          onChange={handleChange}
          className="w-4 h-4 text-blue-600"
        />
        Open Now
      </label>
      <select
        name="limit"
        onChange={handleChange}
        className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="20">Show 20</option>
        <option value="50">Show 50</option>
        <option value="100">Show 100</option>
      </select>
    </div>
  );
};

export default FilterBar;