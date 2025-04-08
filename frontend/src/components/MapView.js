import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const MapView = ({ properties, center, zoom = 10, height = '400px', clickable = false }) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);

  useEffect(() => {
    // Initialize map if not already created
    if (!mapInstanceRef.current) {
      // Find center if not provided
      let mapCenter = center;
      if (!mapCenter && properties.length > 0) {
        const validProperties = properties.filter(p => p.latitude && p.longitude);
        if (validProperties.length > 0) {
          mapCenter = [validProperties[0].latitude, validProperties[0].longitude];
        } else {
          // Default to center of USA if no valid properties
          mapCenter = [37.0902, -95.7129];
        }
      } else if (!mapCenter) {
        mapCenter = [37.0902, -95.7129]; // Default to center of USA
      }

      // Create map instance
      mapInstanceRef.current = L.map(mapRef.current).setView(mapCenter, zoom);

      // Add tile layer (OpenStreetMap)
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19
      }).addTo(mapInstanceRef.current);
    } else {
      // If already initialized, just update the view
      if (center) {
        mapInstanceRef.current.setView(center, zoom);
      }
    }

    // Clear existing markers
    if (mapInstanceRef.current) {
      mapInstanceRef.current.eachLayer(layer => {
        if (layer instanceof L.Marker) {
          mapInstanceRef.current.removeLayer(layer);
        }
      });
    }

    // Add property markers
    properties.forEach(property => {
      if (property.latitude && property.longitude) {
        // Create custom marker icon
        const getMarkerColor = (score) => {
          if (!score) return '#6B7280'; // gray for no score
          if (score >= 85) return '#22c55e'; // green
          if (score >= 70) return '#16a34a'; // dark green
          if (score >= 55) return '#ca8a04'; // yellow
          if (score >= 40) return '#ea580c'; // orange
          return '#dc2626'; // red
        };

        const markerHtml = `
          
            ${property.score ? Math.round(property.score) : '?'}
          
        `;

        const icon = L.divIcon({
          html: markerHtml,
          className: 'custom-marker',
          iconSize: [32, 32],
          iconAnchor: [16, 16]
        });

        // Create marker
        const marker = L.marker([property.latitude, property.longitude], { icon }).addTo(mapInstanceRef.current);

        // Add popup with property info
        const popupContent = `
          
            ${property.address}
            ${property.city}, ${property.state}
            ${property.price.toLocaleString()}
            ${property.bedrooms} bd | ${property.bathrooms} ba | ${property.sqft.toLocaleString()} sqft
            ${clickable ? `View Details` : ''}
          
        `;
        marker.bindPopup(popupContent);
      }
    });

    // Fit bounds to markers if we have properties and no specific center
    if (!center && properties.length > 0) {
      const validProperties = properties.filter(p => p.latitude && p.longitude);
      if (validProperties.length > 0) {
        const bounds = validProperties.map(p => [p.latitude, p.longitude]);
        mapInstanceRef.current.fitBounds(bounds);
      }
    }

    // Cleanup
    return () => {
      if (mapInstanceRef.current) {
        // We'll keep the map instance, just clean up if needed
      }
    };
  }, [properties, center, zoom, clickable]);

  return ;
};

export default MapView;
```

#### frontend/src/components/MarketMetricsChart.js

```jsx
import React from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const MarketMetricsChart = ({ properties }) => {
  // Filter properties with sufficient metrics data
  const validProperties = properties.filter(p => 
    p.metrics && p.metrics.cap_rate && p.metrics.cash_on_cash_return && p.metrics.roi
  );

  if (validProperties.length === 0) {
    return (
      
        No properties with complete metrics data available.
      
    );
  }

  // Group properties by city or state for comparison
  const groupByCity = validProperties.reduce((groups, property) => {
    const city = property.city || 'Unknown';
    if (!groups[city]) {
      groups[city] = [];
    }
    groups[city].push(property);
    return groups;
  }, {});

  // Calculate average metrics for each city
  const cityMetrics = Object.entries(groupByCity).map(([city, cityProperties]) => {
    const avgCapRate = cityProperties.reduce((sum, p) => sum + p.metrics.cap_rate, 0) / cityProperties.length;
    const avgCashOnCash = cityProperties.reduce((sum, p) => sum + p.metrics.cash_on_cash_return, 0) / cityProperties.length;
    const avgRoi = cityProperties.reduce((sum, p) => sum + (p.metrics.roi?.annualized_roi || 0), 0) / cityProperties.length;
    const avgCashFlow = cityProperties.reduce((sum, p) => sum + p.metrics.monthly_cash_flow, 0) / cityProperties.length;
    
    return {
      city,
      count: cityProperties.length,
      avgCapRate,
      avgCashOnCash,
      avgRoi,
      avgCashFlow
    };
  }).sort((a, b) => b.avgCapRate - a.avgCapRate).slice(0, 5); // Top 5 cities by cap rate

  // Chart data
  const data = {
    labels: cityMetrics.map(m => `${m.city} (${m.count})`),
    datasets: [
      {
        label: 'Cap Rate (%)',
        data: cityMetrics.map(m => m.avgCapRate),
        backgroundColor: 'rgba(54, 162, 235, 0.6)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1
      },
      {
        label: 'Cash on Cash (%)',
        data: cityMetrics.map(m => m.avgCashOnCash),
        backgroundColor: 'rgba(75, 192, 192, 0.6)',
        borderColor: 'rgba(75, 192, 192, 1)',
        borderWidth: 1
      },
      {
        label: '5yr Annualized ROI (%)',
        data: cityMetrics.map(m => m.avgRoi),
        backgroundColor: 'rgba(153, 102, 255, 0.6)',
        borderColor: 'rgba(153, 102, 255, 1)',
        borderWidth: 1
      }
    ]
  };

  // Chart options
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom'
      },
      title: {
        display: true,
        text: 'Investment Metrics by Location'
      },
      tooltip: {
        callbacks: {
          afterBody: function(context) {
            const cityIndex = context[0].dataIndex;
            return `Avg. Monthly Cash Flow: ${Math.round(cityMetrics[cityIndex].avgCashFlow).toLocaleString()}`;
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Percentage (%)'
        }
      }
    }
  };

  return (
    <div
      ref={mapRef}
      syle={{ height: '400px', width: '100%' }}
      className="rounded-lg shadow-lg overflow-hidden bg-white"
    >
    
      
    
  );
};

export default MarketMetricsChart;