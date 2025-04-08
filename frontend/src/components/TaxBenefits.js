import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
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
  const [error, setError] = useState(null);

  // Custom analysis parameters
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
      try {
        // Fetch property details
        const propertyRes = await axios.get(`/api/properties/${id}`);
        setProperty(propertyRes.data);

        // Fetch property analysis
        const analysisRes = await axios.get(`/api/analysis/property/${id}`);
        setAnalysis(analysisRes.data);

        // Fetch similar properties
        const similarRes = await axios.get(`/api/properties/similar/${id}`);
        setSimilarProperties(similarRes.data);

        setIsLoading(false);
      } catch (err) {
        setError('Failed to fetch property details. Please try again later.');
        setIsLoading(false);
        console.error('Error fetching property details:', err);
      }
    };

    fetchPropertyData();
  }, [id]);

  // Handle custom analysis parameter changes
  const handleParamChange = (name, value) => {
    setCustomParams({
      ...customParams,
      [name]: value
    });
  };

  // Run custom analysis with current parameters
  const runCustomAnalysis = async () => {
    try {
      setIsLoading(true);
      const response = await axios.post(`/api/analysis/property/${id}`, customParams);
      setAnalysis(response.data);
      setIsLoading(false);
    } catch (err) {
      setError('Failed to run custom analysis.');
      setIsLoading(false);
      console.error('Error running custom analysis:', err);
    }
  };

  if (isLoading) {
    return 
      
    ;
  }

  if (error) {
    return {error};
  }

  if (!property || !analysis) {
    return Property not found.;
  }

  return (
    
      
        
          ← Back to properties
        
      

      {/* Property Header */}
      
        
          
            
              {property.address}
              {property.city}, {property.state} {property.zip_code}
            
            
              
                ${property.price.toLocaleString()}
              
              
                
                  {property.score}
                
                Investment Score
              
            
          

          
            
              
              {property.bedrooms} Bedrooms
            
            
              
              {property.bathrooms} Bathrooms
            
            
              
              {property.sqft.toLocaleString()} sq ft
            
            
              
              Built in {property.year_built}
            
          
        

        
      

      {/* Tabs Navigation */}
      
        
          
            <button
              className={`px-6 py-4 text-sm font-medium ${activeTab === 'overview' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
              onClick={() => setActiveTab('overview')}
            >
              Overview
            
            <button
              className={`px-6 py-4 text-sm font-medium ${activeTab === 'financial' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
              onClick={() => setActiveTab('financial')}
            >
              Financial Analysis
            
            <button
              className={`px-6 py-4 text-sm font-medium ${activeTab === 'financing' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
              onClick={() => setActiveTab('financing')}
            >
              Financing Options
            
            <button
              className={`px-6 py-4 text-sm font-medium ${activeTab === 'tax' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
              onClick={() => setActiveTab('tax')}
            >
              Tax Benefits
            
            <button
              className={`px-6 py-4 text-sm font-medium ${activeTab === 'location' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
              onClick={() => setActiveTab('location')}
            >
              Location
            
          
        

        {/* Tab Content */}
        
          {activeTab === 'overview' && (
            
              Property Overview
              
                
                  Description
                  
                    {property.description || 'No description available.'}
                  
                  
                  Key Investment Metrics
                  
                    Monthly Cash Flow
                    
                      ${analysis.financial_analysis.monthly_cash_flow.toLocaleString()}
                    
                    Cap Rate
                    
                      {analysis.financial_analysis.cap_rate}%
                    
                    Cash-on-Cash Return
                    
                      {analysis.financial_analysis.cash_on_cash_return}%
                    
                    ROI (5yr)
                    
                      {analysis.financial_analysis.roi.annualized_roi}%
                    
                    Break-even Point
                    
                      {analysis.financial_analysis.break_even_point} years
                    
                  
                
                
                
                  Property Details
                  
                    Property Type
                    {formatPropertyType(property.property_type)}
                    Lot Size
                    {property.lot_size || 'N/A'}
                    Price per Sq Ft
                    
                      ${Math.round(property.price / property.sqft).toLocaleString()}
                    
                    Days on Market
                    {property.days_on_market || 'N/A'}
                    Last Updated
                    
                      {new Date(property.updated_at).toLocaleDateString()}
                    
                    Source
                    {property.source}
                    Listing URL
                    
                      
                        View original listing
                      
                    
                  
                
              
            
          )}

          {activeTab === 'financial' && (
            
              Financial Analysis
              
            
          )}

          {activeTab === 'financing' && (
            
              Financing Options
              
            
          )}

          {activeTab === 'tax' && (
            
              Tax Benefits
              
            
          )}

          {activeTab === 'location' && (
            
              Location Analysis
              
                
                  
                  
                  Market Data
                  
                    Property Tax Rate
                    
                      {(analysis.market_data.property_tax_rate * 100).toFixed(2)}%
                    
                    Vacancy Rate
                    
                      {(analysis.market_data.vacancy_rate * 100).toFixed(2)}%
                    
                    Price-to-Rent Ratio
                    
                      {analysis.market_data.price_to_rent_ratio}
                    
                    Appreciation Rate
                    
                      {(analysis.market_data.appreciation_rate * 100).toFixed(2)}%
                    
                  
                
                
                
                  Neighborhood Stats
                  
                    Schools Rating
                    
                      {analysis.market_data.school_rating || 'N/A'}/10
                    
                    Crime Rating
                    
                      {analysis.market_data.crime_rating || 'N/A'}/10
                    
                    Walk Score
                    
                      {analysis.market_data.walk_score || 'N/A'}/100
                    
                    Transit Score
                    
                      {analysis.market_data.transit_score || 'N/A'}/100
                    
                  
                  
                  Local Incentives
                  {analysis.tax_benefits.local_tax_incentives.special_programs.length > 0 ? (
                    
                      {analysis.tax_benefits.local_tax_incentives.special_programs.map((program, index) => (
                        {program}
                      ))}
                    
                  ) : (
                    No special tax or financing programs were found for this location.
                  )}
                
              
            
          )}
        
      

      {/* Similar Properties */}
      {similarProperties.length > 0 && (
        
          Similar Properties
          
        
      )}
    
  );
};

// Helper function to get color based on score
function getScoreColor(score) {
  if (score >= 85) return '#22c55e'; // green-500
  if (score >= 70) return '#16a34a'; // green-600
  if (score >= 55) return '#ca8a04'; // yellow-600
  if (score >= 40) return '#ea580c'; // orange-600
  return '#dc2626'; // red-600
}

// Helper function to format property type
function formatPropertyType(type) {
  if (!type) return 'N/A';
  return type.split('_').map(word =>
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ');
}

export default PropertyDetail;