import React from 'react';
import { Link } from 'react-router-dom';

const ComparisonTable = ({ properties }) => {
  if (!properties || properties.length === 0) {
    return <div className="text-gray-500 text-center py-4">No properties to compare.</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead>
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Property</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Price</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Beds/Baths</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sq Ft</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cap Rate</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cash Flow</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Score</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {properties.map((property, index) => (
            <tr key={property._id || index} className="hover:bg-gray-50">
              <td className="px-4 py-3">
                <Link to={`/property/${property._id}`} className="text-blue-600 hover:text-blue-800 text-sm">
                  {property.address}
                </Link>
                <p className="text-xs text-gray-500">{property.city}, {property.state}</p>
              </td>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">
                ${property.price?.toLocaleString()}
              </td>
              <td className="px-4 py-3 text-sm text-gray-600">
                {property.bedrooms}/{property.bathrooms}
              </td>
              <td className="px-4 py-3 text-sm text-gray-600">
                {property.sqft?.toLocaleString()}
              </td>
              <td className="px-4 py-3 text-sm text-blue-600 font-medium">
                {property.metrics?.cap_rate || 'N/A'}%
              </td>
              <td className={`px-4 py-3 text-sm font-medium ${
                (property.metrics?.monthly_cash_flow || 0) >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                ${property.metrics?.monthly_cash_flow || 'N/A'}
              </td>
              <td className="px-4 py-3 text-sm font-bold">
                {property.score || 'N/A'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ComparisonTable;
