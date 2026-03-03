import React from 'react';
import { Link } from 'react-router-dom';

const PropertyCard = ({ property }) => {
  const getScoreColor = (score) => {
    if (!score) return '#6B7280';
    if (score >= 85) return '#22c55e';
    if (score >= 70) return '#16a34a';
    if (score >= 55) return '#ca8a04';
    if (score >= 40) return '#ea580c';
    return '#dc2626';
  };

  return (
    <Link to={`/property/${property._id}`} className="block">
      <div className="border rounded-lg overflow-hidden hover:shadow-md transition-shadow">
        {property.images && property.images.length > 0 ? (
          <img
            src={property.images[0]}
            alt={property.address}
            className="w-full h-40 object-cover"
          />
        ) : (
          <div className="w-full h-40 bg-gray-200 flex items-center justify-center">
            <span className="text-gray-400">No image</span>
          </div>
        )}
        <div className="p-4">
          <div className="flex justify-between items-start mb-2">
            <div>
              <p className="font-semibold text-gray-900 truncate">{property.address}</p>
              <p className="text-sm text-gray-500">{property.city}, {property.state}</p>
            </div>
            {property.score && (
              <span
                className="inline-flex items-center justify-center w-8 h-8 rounded-full text-white text-xs font-bold"
                style={{ backgroundColor: getScoreColor(property.score) }}
              >
                {Math.round(property.score)}
              </span>
            )}
          </div>
          <p className="text-lg font-bold text-green-600 mb-2">
            ${property.price?.toLocaleString()}
          </p>
          <div className="flex text-sm text-gray-600 space-x-3">
            <span>{property.bedrooms} bd</span>
            <span>{property.bathrooms} ba</span>
            <span>{property.sqft?.toLocaleString()} sqft</span>
          </div>
          {property.metrics && (
            <div className="mt-2 pt-2 border-t flex justify-between text-xs text-gray-500">
              <span>Cap Rate: {property.metrics.cap_rate || 'N/A'}%</span>
              <span>Cash Flow: ${property.metrics.monthly_cash_flow || 'N/A'}</span>
            </div>
          )}
        </div>
      </div>
    </Link>
  );
};

export default PropertyCard;
