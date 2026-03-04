import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../services/api';
import InvestmentMetrics from './InvestmentMetrics';
import PropertyGallery from './PropertyGallery';
import FinancingCalculator from './FinancingCalculator';
import TaxBenefits from './TaxBenefits';
import MapView from './MapView';
import ComparisonTable from './ComparisonTable';

const PropertyDetail = () => {
  const { id } = useParams();
  const [property, setProperty] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [similarProperties, setSimilarProperties] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState(null);

  const [customParams, setCustomParams] = useState({
    down_payment_percentage: 0.20,
    interest_rate: 0.045,
    term_years: 30,
    holding_period: 5,
    appreciation_rate: 0.03,
    tax_bracket: 0.22,
    credit_score: 720,
    veteran: false,
    first_time_va: true
  });

  useEffect(() => {
    const fetchPropertyData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const propertyRes = await api.getProperty(id);
        setProperty(propertyRes.data);

        const analysisRes = await api.getPropertyAnalysis(id);
        setAnalysis(analysisRes.data);

        try {
          const similarRes = await api.getProperties({ limit: 4 });
          const similarList = similarRes.data.data || [];
          setSimilarProperties(similarList.filter(p => p._id !== id).slice(0, 3));
        } catch (e) {
          setSimilarProperties([]);
        }

        setIsLoading(false);
      } catch (err) {
        setError('Failed to fetch property details. Please try again later.');
        setIsLoading(false);
      }
    };

    fetchPropertyData();
  }, [id]);

  const handleParamChange = (name, value) => {
    setCustomParams({ ...customParams, [name]: value });
  };

  const runCustomAnalysis = async () => {
    try {
      setIsAnalyzing(true);
      const response = await api.customizeAnalysis(id, customParams);
      setAnalysis(response.data);
      setIsAnalyzing(false);
    } catch (err) {
      setError('Failed to run custom analysis.');
      setIsAnalyzing(false);
    }
  };

  if (isLoading) {
    return <div className="text-center py-10 text-gray-600">Loading property details...</div>;
  }

  if (error) {
    return <div className="text-center py-10 text-red-600">{error}</div>;
  }

  if (!property || !analysis) {
    return <div className="text-center py-10 text-gray-600">Property not found.</div>;
  }

  return (
    <div>
      <div className="mb-4">
        <Link to="/" className="text-blue-600 hover:text-blue-800">
          &larr; Back to properties
        </Link>
      </div>

      {/* Property Header */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{property.address}</h1>
            <p className="text-gray-600">{property.city}, {property.state} {property.zip_code}</p>
          </div>
          <div className="flex items-center space-x-4 mt-2 md:mt-0">
            <span className="text-3xl font-bold text-green-600">
              ${property.price.toLocaleString()}
            </span>
            <div className="text-center">
              <span
                className="inline-block w-12 h-12 rounded-full text-white font-bold text-lg flex items-center justify-center"
                style={{ backgroundColor: getScoreColor(property.score) }}
              >
                {property.score || '?'}
              </span>
              <span className="text-xs text-gray-500">Investment Score</span>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-4 text-gray-600">
          <span>{property.bedrooms} Bedrooms</span>
          <span>{property.bathrooms} Bathrooms</span>
          <span>{property.sqft?.toLocaleString()} sq ft</span>
          <span>Built in {property.year_built}</span>
        </div>

        <PropertyGallery images={property.images} />
      </div>

      {/* Tabs Navigation */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="border-b">
          <nav className="flex overflow-x-auto">
            {['overview', 'financial', 'financing', 'tax', 'location'].map(tab => (
              <button
                key={tab}
                className={`px-6 py-4 text-sm font-medium whitespace-nowrap ${
                  activeTab === tab
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
                onClick={() => setActiveTab(tab)}
              >
                {tab === 'overview' ? 'Overview' :
                 tab === 'financial' ? 'Financial Analysis' :
                 tab === 'financing' ? 'Financing Options' :
                 tab === 'tax' ? 'Tax Benefits' : 'Location'}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'overview' && (
            <div>
              <h2 className="text-xl font-semibold mb-4">Property Overview</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="font-semibold text-gray-700 mb-2">Description</h3>
                  <p className="text-gray-600 mb-4">
                    {property.description || 'No description available.'}
                  </p>
                  <h3 className="font-semibold text-gray-700 mb-2">Key Investment Metrics</h3>
                  <dl className="space-y-2">
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Monthly Cash Flow</dt>
                      <dd className="font-medium">${(analysis.financial_analysis?.monthly_cash_flow ?? 0).toLocaleString()}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Cap Rate</dt>
                      <dd className="font-medium">{analysis.financial_analysis.cap_rate}%</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Cash-on-Cash Return</dt>
                      <dd className="font-medium">{analysis.financial_analysis.cash_on_cash_return}%</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">ROI (5yr)</dt>
                      <dd className="font-medium">{analysis.financial_analysis.roi.annualized_roi}%</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Break-even Point</dt>
                      <dd className="font-medium">{analysis.financial_analysis.break_even_point} years</dd>
                    </div>
                  </dl>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-700 mb-2">Property Details</h3>
                  <dl className="space-y-2">
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Property Type</dt>
                      <dd className="font-medium">{formatPropertyType(property.property_type)}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Lot Size</dt>
                      <dd className="font-medium">{property.lot_size || 'N/A'}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Price per Sq Ft</dt>
                      <dd className="font-medium">${property.sqft ? Math.round(property.price / property.sqft).toLocaleString() : 'N/A'}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Source</dt>
                      <dd className="font-medium">{property.source}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Listing URL</dt>
                      <dd>
                        {property.listing_url && /^https?:\/\//i.test(property.listing_url) ? (
                          <a href={property.listing_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800">
                            View original listing
                          </a>
                        ) : (
                          <span className="text-gray-400">N/A</span>
                        )}
                      </dd>
                    </div>
                  </dl>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'financial' && (
            <div>
              <h2 className="text-xl font-semibold mb-4">Financial Analysis</h2>
              <InvestmentMetrics analysis={analysis.financial_analysis} />
            </div>
          )}

          {activeTab === 'financing' && (
            <div>
              <h2 className="text-xl font-semibold mb-4">Financing Options</h2>
              {isAnalyzing && <div className="text-center py-4 text-gray-500">Recalculating...</div>}
              <FinancingCalculator
                property={property}
                financingOptions={analysis.financing_options}
                onParamChange={handleParamChange}
                params={customParams}
                onAnalyze={runCustomAnalysis}
              />
            </div>
          )}

          {activeTab === 'tax' && (
            <div>
              <h2 className="text-xl font-semibold mb-4">Tax Benefits</h2>
              <TaxBenefits taxBenefits={analysis.tax_benefits} />
            </div>
          )}

          {activeTab === 'location' && (
            <div>
              <h2 className="text-xl font-semibold mb-4">Location Analysis</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <MapView
                    properties={[property]}
                    center={property.latitude && property.longitude ? [property.latitude, property.longitude] : undefined}
                    zoom={14}
                  />
                  <h3 className="font-semibold text-gray-700 mt-4 mb-2">Market Data</h3>
                  <dl className="space-y-2">
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Property Tax Rate</dt>
                      <dd className="font-medium">{(analysis.market_data.property_tax_rate * 100).toFixed(2)}%</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Vacancy Rate</dt>
                      <dd className="font-medium">{(analysis.market_data.vacancy_rate * 100).toFixed(2)}%</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Price-to-Rent Ratio</dt>
                      <dd className="font-medium">{analysis.market_data.price_to_rent_ratio}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Appreciation Rate</dt>
                      <dd className="font-medium">{(analysis.market_data.appreciation_rate * 100).toFixed(2)}%</dd>
                    </div>
                  </dl>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-700 mb-2">Neighborhood Stats</h3>
                  <dl className="space-y-2">
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Schools Rating</dt>
                      <dd className="font-medium">{analysis.market_data.school_rating || 'N/A'}/10</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Crime Rating</dt>
                      <dd className="font-medium">{analysis.market_data.crime_rating || 'N/A'}/10</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Walk Score</dt>
                      <dd className="font-medium">{analysis.market_data.walk_score || 'N/A'}/100</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Transit Score</dt>
                      <dd className="font-medium">{analysis.market_data.transit_score || 'N/A'}/100</dd>
                    </div>
                  </dl>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Similar Properties */}
      {similarProperties.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Similar Properties</h2>
          <ComparisonTable properties={similarProperties} />
        </div>
      )}
    </div>
  );
};

function getScoreColor(score) {
  if (!score) return '#6B7280';
  if (score >= 85) return '#22c55e';
  if (score >= 70) return '#16a34a';
  if (score >= 55) return '#ca8a04';
  if (score >= 40) return '#ea580c';
  return '#dc2626';
}

function formatPropertyType(type) {
  if (!type) return 'N/A';
  return type.split('_').map(word =>
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ');
}

export default PropertyDetail;
