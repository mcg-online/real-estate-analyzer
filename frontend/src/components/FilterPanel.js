import React from 'react';

const FilterPanel = ({ filters, onFilterChange, resultsCount }) => {
  const handleChange = (e) => {
    const { name, value } = e.target;
    onFilterChange({ [name]: value });
  };

  return (
    <div className="space-y-4" role="form" aria-label="Property filters">
      <div role="group" aria-labelledby="price-range-heading">
        <h3 id="price-range-heading" className="sr-only">Price Range</h3>
        <div className="mb-4">
          <label htmlFor="filter-min-price" className="block text-sm font-medium text-gray-700 mb-1">Min Price</label>
          <input
            id="filter-min-price"
            type="number"
            name="minPrice"
            value={filters.minPrice}
            onChange={handleChange}
            placeholder="e.g. 100000"
            aria-label="Minimum price in dollars"
            className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-blue-500"
          />
        </div>
        <div>
          <label htmlFor="filter-max-price" className="block text-sm font-medium text-gray-700 mb-1">Max Price</label>
          <input
            id="filter-max-price"
            type="number"
            name="maxPrice"
            value={filters.maxPrice}
            onChange={handleChange}
            placeholder="e.g. 500000"
            aria-label="Maximum price in dollars"
            className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>
      <div role="group" aria-labelledby="rooms-heading">
        <h3 id="rooms-heading" className="sr-only">Room Requirements</h3>
        <div className="mb-4">
          <label htmlFor="filter-min-bedrooms" className="block text-sm font-medium text-gray-700 mb-1">Min Bedrooms</label>
          <select
            id="filter-min-bedrooms"
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
          <label htmlFor="filter-min-bathrooms" className="block text-sm font-medium text-gray-700 mb-1">Min Bathrooms</label>
          <select
            id="filter-min-bathrooms"
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
      </div>
      <div>
        <label htmlFor="filter-property-type" className="block text-sm font-medium text-gray-700 mb-1">Property Type</label>
        <select
          id="filter-property-type"
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
        <label htmlFor="filter-min-score" className="block text-sm font-medium text-gray-700 mb-1">
          Min Score: {filters.minScore}
        </label>
        <input
          id="filter-min-score"
          type="range"
          name="minScore"
          min="0"
          max="100"
          value={filters.minScore}
          onChange={handleChange}
          aria-label={`Minimum investment score, currently ${filters.minScore} out of 100`}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={filters.minScore}
          className="w-full"
        />
      </div>
      {resultsCount !== undefined && (
        <div aria-live="polite" aria-atomic="true" className="text-sm text-gray-600">
          {resultsCount === 0
            ? 'No properties match your filters.'
            : `${resultsCount} ${resultsCount === 1 ? 'property' : 'properties'} found.`}
        </div>
      )}
      <button
        onClick={() => onFilterChange({
          minPrice: '', maxPrice: '', minBedrooms: '',
          minBathrooms: '', propertyType: '', minScore: 70
        })}
        aria-label="Reset all filters to default values"
        className="w-full bg-gray-100 text-gray-700 py-2 px-4 rounded hover:bg-gray-200 text-sm font-medium"
      >
        Reset Filters
      </button>
    </div>
  );
};

export default FilterPanel;
