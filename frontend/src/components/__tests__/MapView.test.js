import React from 'react';
import { render } from '@testing-library/react';
import L from 'leaflet';
import MapView from '../MapView';

// Reset leaflet mocks before each test
beforeEach(() => {
  jest.clearAllMocks();

  // Re-setup ALL mock implementations after clearAllMocks wipes them
  const markerInstance = {
    addTo: jest.fn().mockReturnThis(),
    bindPopup: jest.fn().mockReturnThis(),
    remove: jest.fn(),
  };
  const mapInstance = {
    setView: jest.fn().mockReturnThis(),
    remove: jest.fn(),
    eachLayer: jest.fn(),
    removeLayer: jest.fn(),
    fitBounds: jest.fn(),
  };
  const tileLayerInstance = {
    addTo: jest.fn(),
  };

  L.map.mockReturnValue(mapInstance);
  L.tileLayer.mockReturnValue(tileLayerInstance);
  L.marker.mockReturnValue(markerInstance);
  L.divIcon.mockImplementation((opts) => opts);
});

const propertiesWithCoords = [
  {
    _id: 'p1',
    address: '123 Main St',
    city: 'Austin',
    state: 'TX',
    price: 300000,
    bedrooms: 3,
    bathrooms: 2,
    sqft: 1500,
    latitude: 30.2672,
    longitude: -97.7431,
    score: 85,
  },
  {
    _id: 'p2',
    address: '456 Elm St',
    city: 'Dallas',
    state: 'TX',
    price: 250000,
    bedrooms: 2,
    bathrooms: 1,
    sqft: 1200,
    latitude: 32.7767,
    longitude: -96.7970,
    score: 60,
  },
];

describe('MapView', () => {
  it('renders a map container div', () => {
    const { container } = render(<MapView properties={[]} />);
    const mapDiv = container.firstChild;
    expect(mapDiv).toBeInTheDocument();
    expect(mapDiv).toHaveStyle({ height: '400px', width: '100%' });
  });

  it('initializes the Leaflet map', () => {
    render(<MapView properties={[]} />);
    expect(L.map).toHaveBeenCalledTimes(1);
  });

  it('adds a tile layer to the map', () => {
    render(<MapView properties={[]} />);
    expect(L.tileLayer).toHaveBeenCalledWith(
      'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      expect.objectContaining({ maxZoom: 19 })
    );
  });

  it('creates markers for properties with coordinates', () => {
    render(<MapView properties={propertiesWithCoords} />);
    // Two properties, two markers
    expect(L.marker).toHaveBeenCalledTimes(2);
    expect(L.marker).toHaveBeenCalledWith([30.2672, -97.7431], expect.any(Object));
    expect(L.marker).toHaveBeenCalledWith([32.7767, -96.7970], expect.any(Object));
  });

  it('does not create markers for properties without coordinates', () => {
    const noCoords = [{ _id: 'p3', address: '789 Pine', city: 'Miami', state: 'FL', price: 500000 }];
    render(<MapView properties={noCoords} />);
    expect(L.marker).not.toHaveBeenCalled();
  });

  it('creates divIcon with score for each property', () => {
    render(<MapView properties={propertiesWithCoords} />);
    expect(L.divIcon).toHaveBeenCalledTimes(2);
    // Check the first call includes the score in the HTML
    const firstIconCall = L.divIcon.mock.calls[0][0];
    expect(firstIconCall.html).toContain('85');
    const secondIconCall = L.divIcon.mock.calls[1][0];
    expect(secondIconCall.html).toContain('60');
  });

  it('uses custom height when provided', () => {
    const { container } = render(<MapView properties={[]} height="600px" />);
    expect(container.firstChild).toHaveStyle({ height: '600px' });
  });

  it('uses default US center when no properties and no center provided', () => {
    const mapInstance = L.map();
    render(<MapView properties={[]} />);
    expect(mapInstance.setView).toHaveBeenCalledWith([37.0902, -95.7129], 10);
  });

  it('uses provided center when specified', () => {
    const mapInstance = L.map();
    render(<MapView properties={propertiesWithCoords} center={[40.7128, -74.0060]} zoom={12} />);
    expect(mapInstance.setView).toHaveBeenCalledWith([40.7128, -74.0060], 12);
  });
});
