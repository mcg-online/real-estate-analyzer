import React from 'react';

const TopMarketsTable = ({ markets }) => {
  if (!markets || markets.length === 0) {
    return <div className="text-gray-500 text-center py-4">No market data available.</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead>
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Rank</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Market</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Avg. ROI</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cap Rate</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Avg. Price</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {markets.map((market, index) => (
            <tr key={index} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-sm font-medium text-gray-900">{index + 1}</td>
              <td className="px-4 py-3 text-sm text-gray-900">{market.name || market.market_name || `Market ${index + 1}`}</td>
              <td className="px-4 py-3 text-sm text-green-600 font-medium">{market.avg_roi?.toFixed(2) || 'N/A'}%</td>
              <td className="px-4 py-3 text-sm text-blue-600 font-medium">{market.avg_cap_rate?.toFixed(2) || 'N/A'}%</td>
              <td className="px-4 py-3 text-sm text-gray-600">${market.avg_price?.toLocaleString() || 'N/A'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default TopMarketsTable;
