import React from 'react';

const FilterPanel = ({ filters, onFilterChange }) => {
  const handleChange = (e) => {
    const { name, value } = e.target;
    onFilterChange({ [name]: value });
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Min Price</label>
        <input
          type="number"
          name="minPrice"
          value={filters.minPrice}
          onChange={handleChange}
          placeholder="e.g. 100000"
          className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-blue-500"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Max Price</label>
        <input
          type="number"
          name="maxPrice"
          value={filters.maxPrice}
          onChange={handleChange}
          placeholder="e.g. 500000"
          className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-blue-500"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Min Bedrooms</label>
        <select
          name="minBedrooms"
          value={filters.minBedrooms}
          onChange={handleChange}
          className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">Any</option>
          <option value="1">1+</option>
          <option value="2">2+</option>
          <option value="3">3+</option>
          <option value="4">4+</option>
          <option value="5">5+</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Min Bathrooms</label>
        <select
          name="minBathrooms"
          value={filters.minBathrooms}
          onChange={handleChange}
          className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">Any</option>
          <option value="1">1+</option>
          <option value="1.5">1.5+</option>
          <option value="2">2+</option>
          <option value="3">3+</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Property Type</label>
        <select
          name="propertyType"
          value={filters.propertyType}
          onChange={handleChange}
          className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">All Types</option>
          <option value="Residential">Residential</option>
          <option value="Condo">Condo</option>
          <option value="Townhouse">Townhouse</option>
          <option value="Multi-Family">Multi-Family</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Min Score: {filters.minScore}
        </label>
        <input
          type="range"
          name="minScore"
          min="0"
          max="100"
          value={filters.minScore}
          onChange={handleChange}
          className="w-full"
        />
      </div>
      <button
        onClick={() => onFilterChange({
          minPrice: '', maxPrice: '', minBedrooms: '',
          minBathrooms: '', propertyType: '', minScore: 70
        })}
        className="w-full bg-gray-100 text-gray-700 py-2 px-4 rounded hover:bg-gray-200 text-sm font-medium"
      >
        Reset Filters
      </button>
    </div>
  );
};

export default FilterPanel;
