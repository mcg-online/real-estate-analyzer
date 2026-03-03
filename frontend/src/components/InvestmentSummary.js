import React from 'react';

const InvestmentSummary = ({ properties }) => {
  if (!properties || properties.length === 0) {
    return <div className="text-gray-500 text-center py-4">No properties to summarize.</div>;
  }

  const withMetrics = properties.filter(p => p.metrics);
  const totalValue = properties.reduce((sum, p) => sum + (p.price || 0), 0);
  const avgPrice = totalValue / properties.length;

  const avgCapRate = withMetrics.length > 0
    ? withMetrics.reduce((sum, p) => sum + (p.metrics.cap_rate || 0), 0) / withMetrics.length
    : 0;

  const avgCashFlow = withMetrics.length > 0
    ? withMetrics.reduce((sum, p) => sum + (p.metrics.monthly_cash_flow || 0), 0) / withMetrics.length
    : 0;

  const avgRoi = withMetrics.length > 0
    ? withMetrics.reduce((sum, p) => sum + (p.metrics.roi?.annualized_roi || 0), 0) / withMetrics.length
    : 0;

  const avgScore = properties.filter(p => p.score).length > 0
    ? properties.filter(p => p.score).reduce((sum, p) => sum + p.score, 0) / properties.filter(p => p.score).length
    : 0;

  const stats = [
    { label: 'Total Properties', value: properties.length, format: 'number' },
    { label: 'Total Portfolio Value', value: totalValue, format: 'currency' },
    { label: 'Avg. Property Price', value: avgPrice, format: 'currency' },
    { label: 'Avg. Cap Rate', value: avgCapRate, format: 'percent' },
    { label: 'Avg. Monthly Cash Flow', value: avgCashFlow, format: 'currency' },
    { label: 'Avg. Annualized ROI', value: avgRoi, format: 'percent' },
    { label: 'Avg. Investment Score', value: avgScore, format: 'score' },
  ];

  const formatValue = (value, format) => {
    switch (format) {
      case 'currency': return `$${Math.round(value).toLocaleString()}`;
      case 'percent': return `${value.toFixed(2)}%`;
      case 'score': return Math.round(value).toString();
      default: return value.toString();
    }
  };

  return (
    <div className="space-y-3">
      {stats.map((stat, index) => (
        <div key={index} className="flex justify-between items-center py-2 border-b last:border-b-0">
          <span className="text-gray-600 text-sm">{stat.label}</span>
          <span className="font-semibold text-gray-900">{formatValue(stat.value, stat.format)}</span>
        </div>
      ))}
    </div>
  );
};

export default InvestmentSummary;
