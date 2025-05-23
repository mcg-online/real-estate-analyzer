import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import PropertyCard from './PropertyCard';
import InvestmentSummary from './InvestmentSummary';
import MarketMetricsChart from './MarketMetricsChart';
import MapView from './MapView';
import FilterPanel from './FilterPanel';
import TopMarketsTable from './TopMarketsTable';
import { Bar, Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';

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
  })
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

  // Fetch data when component mounts or filters change
  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        // Build query params for filtering
        const queryParams = Object.entries(filters)
          .filter(([_, value]) => value !== '')
          .map(([key, value]) => `${key}=${value}`)
          .join('&');

        // Fetch properties
        const propertiesResponse = await axios.get(`/api/properties?${queryParams}`);
        setProperties(propertiesResponse.data);

        // Set top properties (highest score)
        const sorted = [...propertiesResponse.data].sort((a, b) => b.score - a.score);
        setTopProperties(sorted.slice(0, 4));

        // Fetch top markets
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
    return 
      
    ;
  }

  if (error) {
    return {error};
  }

  return (
    
      
        Investment Dashboard
        
          Welcome to your real estate investment dashboard. Here you can see top investment
          opportunities and analyze potential properties.
        
      

      {/* Summary Statistics */}
      
        
          Properties
          {properties.length}
        
        
          Avg. Price
          
            ${properties.length > 0 
              ? Math.round(properties.reduce((sum, p) => sum + p.price, 0) / properties.length).toLocaleString() 
              : 0}
          
        
        
          Avg. ROI
          
            {properties.length > 0 && properties[0].metrics && properties[0].metrics.roi
              ? (properties.reduce((sum, p) => sum + (p.metrics.roi?.annualized_roi || 0), 0) / properties.length).toFixed(2)
              : 0}%
          
        
        
          Avg. Cap Rate
          
            {properties.length > 0 && properties[0].metrics
              ? (properties.reduce((sum, p) => sum + (p.metrics.cap_rate || 0), 0) / properties.length).toFixed(2)
              : 0}%
          
        
      

      
        
          
            Top Investment Opportunities
            {topProperties.length > 0 ? (
              
                {topProperties.map(property => (
                  
                ))}
              
            ) : (
              No properties match your current filters.
            )}
            
              
                View all properties →
              
            
          
        
        
          
            Filter Properties
            
          
        
      

      
        
          
            Property Map
            
          
        
        
          
            Investment Summary
            
          
        
      

      
        
          
            Top Markets by ROI
            
            
              
                View all markets →
              
            
          
        
        
          
            Investment Metrics
            
          
        
      
    
  );
};

export default Dashboard;