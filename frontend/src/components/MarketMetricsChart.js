import React from 'react';
import { Bar } from 'react-chartjs-2';
import '../chartSetup';

const MarketMetricsChart = ({ properties }) => {
  const validProperties = properties.filter(p =>
    p.metrics && p.metrics.cap_rate && p.metrics.cash_on_cash_return && p.metrics.roi
  );

  if (validProperties.length === 0) {
    return (
      <div className="text-center text-gray-500 py-8">
        No properties with complete metrics data available.
      </div>
    );
  }

  const groupByCity = validProperties.reduce((groups, property) => {
    const city = property.city || 'Unknown';
    if (!groups[city]) {
      groups[city] = [];
    }
    groups[city].push(property);
    return groups;
  }, {});

  const cityMetrics = Object.entries(groupByCity).map(([city, cityProperties]) => {
    const avgCapRate = cityProperties.reduce((sum, p) => sum + p.metrics.cap_rate, 0) / cityProperties.length;
    const avgCashOnCash = cityProperties.reduce((sum, p) => sum + p.metrics.cash_on_cash_return, 0) / cityProperties.length;
    const avgRoi = cityProperties.reduce((sum, p) => sum + (p.metrics.roi?.annualized_roi || 0), 0) / cityProperties.length;
    const avgCashFlow = cityProperties.reduce((sum, p) => sum + p.metrics.monthly_cash_flow, 0) / cityProperties.length;

    return { city, count: cityProperties.length, avgCapRate, avgCashOnCash, avgRoi, avgCashFlow };
  }).sort((a, b) => b.avgCapRate - a.avgCapRate).slice(0, 5);

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

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom' },
      title: { display: true, text: 'Investment Metrics by Location' },
      tooltip: {
        callbacks: {
          afterBody: function (context) {
            const cityIndex = context[0].dataIndex;
            return `Avg. Monthly Cash Flow: $${Math.round(cityMetrics[cityIndex].avgCashFlow).toLocaleString()}`;
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: { display: true, text: 'Percentage (%)' }
      }
    }
  };

  return (
    <div style={{ height: '400px', width: '100%' }}>
      <Bar data={data} options={options} />
    </div>
  );
};

export default MarketMetricsChart;
