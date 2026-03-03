import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import PropertyCard from './PropertyCard';
import InvestmentSummary from './InvestmentSummary';
import MarketMetricsChart from './MarketMetricsChart';
import MapView from './MapView';
import FilterPanel from './FilterPanel';
import TopMarketsTable from './TopMarketsTable';
import { Bar } from 'react-chartjs-2';
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

  const renderMetricsComparison = () => {
    const data = {
      labels: topProperties.map(p => p.address.split(',')[0]),
      datasets: [
        {
          label: 'ROI (%)',
          data: topProperties.map(p => p.metrics?.roi?.annualized_roi || 0),
          backgroundColor: 'rgba(54, 162, 235, 0.6)',
        },
        {
          label: 'Cash Flow ($)',
          data: topProperties.map(p => p.metrics?.monthly_cash_flow || 0),
          backgroundColor: 'rgba(75, 192, 192, 0.6)',
        }
      ]
    };

    return (
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4">Investment Metrics Comparison</h2>
        <Bar data={data} height={300} options={{ maintainAspectRatio: false }} />
      </div>
    );
  };

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const queryParams = Object.entries(filters)
          .filter(([_, value]) => value !== '')
          .map(([key, value]) => `${key}=${value}`)
          .join('&');

        const propertiesResponse = await axios.get(`/api/properties?${queryParams}`);
        setProperties(propertiesResponse.data);

        const sorted = [...propertiesResponse.data].sort((a, b) => (b.score || 0) - (a.score || 0));
        setTopProperties(sorted.slice(0, 4));

        const marketsResponse = await axios.get('/api/markets/top?metric=roi&limit=5');
        setTopMarkets(marketsResponse.data);

        setIsLoading(false);
      } catch (err) {
        setError('Failed to fetch data. Please try again later.');
        setIsLoading(false);
        console.error('Error fetching data:', err);
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
