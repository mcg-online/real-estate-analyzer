import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import PropertyCard from './PropertyCard';
import InvestmentSummary from './InvestmentSummary';
import MarketMetricsChart from './MarketMetricsChart';
import MapView from './MapView';
import FilterPanel from './FilterPanel';
import TopMarketsTable from './TopMarketsTable';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const Dashboard = () => {
  const [properties, setProperties] = useState([]);
  const [topProperties, setTopProperties] = useState([]);
  const [topMarkets, setTopMarkets] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    minPrice: '',
    maxPrice: '',
    minBedrooms: '',
    minBathrooms: '',
    propertyType: '',
    minScore: 70
  });

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const filterParams = {};
        Object.entries(filters).forEach(([key, value]) => {
          if (value !== '') filterParams[key] = value;
        });

        const propertiesResponse = await api.getProperties(filterParams);
        const propertiesList = propertiesResponse.data.data || [];
        setProperties(propertiesList);

        const sorted = [...propertiesList].sort((a, b) => (b.score || 0) - (a.score || 0));
        setTopProperties(sorted.slice(0, 4));

        const marketsResponse = await api.getTopMarkets({ metric: 'roi', limit: 5 });
        setTopMarkets(marketsResponse.data);

        setIsLoading(false);
      } catch (err) {
        setError('Failed to fetch data. Please try again later.');
        setIsLoading(false);
      }
    };

    fetchData();
  }, [filters]);

  const handleFilterChange = (newFilters) => {
    setFilters({ ...filters, ...newFilters });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Investment Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Welcome to your real estate investment dashboard. Here you can see top investment
          opportunities and analyze potential properties.
        </p>
      </div>

      {/* Summary Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Properties</p>
          <p className="text-2xl font-bold text-gray-900">{properties.length}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Avg. Price</p>
          <p className="text-2xl font-bold text-gray-900">
            ${properties.length > 0
              ? Math.round(properties.reduce((sum, p) => sum + p.price, 0) / properties.length).toLocaleString()
              : 0}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Avg. ROI</p>
          <p className="text-2xl font-bold text-gray-900">
            {properties.length > 0 && properties[0].metrics && properties[0].metrics.roi
              ? (properties.reduce((sum, p) => sum + (p.metrics.roi?.annualized_roi || 0), 0) / properties.length).toFixed(2)
              : 0}%
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Avg. Cap Rate</p>
          <p className="text-2xl font-bold text-gray-900">
            {properties.length > 0 && properties[0].metrics
              ? (properties.reduce((sum, p) => sum + (p.metrics.cap_rate || 0), 0) / properties.length).toFixed(2)
              : 0}%
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Top Investment Opportunities</h2>
            {topProperties.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {topProperties.map(property => (
                  <PropertyCard key={property._id} property={property} />
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No properties match your current filters.</p>
            )}
            <div className="mt-4 text-center">
              <Link to="/" className="text-blue-600 hover:text-blue-800 font-medium">
                View all properties &rarr;
              </Link>
            </div>
          </div>
        </div>
        <div>
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Filter Properties</h2>
            <FilterPanel filters={filters} onFilterChange={handleFilterChange} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Property Map</h2>
          <MapView properties={properties} clickable={true} />
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Investment Summary</h2>
          <InvestmentSummary properties={properties} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Top Markets by ROI</h2>
          <TopMarketsTable markets={topMarkets} />
          <div className="mt-4 text-center">
            <Link to="/" className="text-blue-600 hover:text-blue-800 font-medium">
              View all markets &rarr;
            </Link>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Investment Metrics</h2>
          <MarketMetricsChart properties={properties} />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
