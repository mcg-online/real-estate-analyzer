import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

const MapView = ({ properties, center, zoom = 10, height = '400px', clickable = false }) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);

  // Initialize map once
  useEffect(() => {
    if (mapInstanceRef.current) return;

    let mapCenter = center;
    if (!mapCenter && properties.length > 0) {
      const validProperties = properties.filter(p => p.latitude && p.longitude);
      if (validProperties.length > 0) {
        mapCenter = [validProperties[0].latitude, validProperties[0].longitude];
      } else {
        mapCenter = [37.0902, -95.7129];
      }
    } else if (!mapCenter) {
      mapCenter = [37.0902, -95.7129];
    }

    mapInstanceRef.current = L.map(mapRef.current).setView(mapCenter, zoom);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19
    }).addTo(mapInstanceRef.current);

    // Cleanup only on unmount
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []); // eslint-disable-line

  // Update markers and view when data changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (center) {
      map.setView(center, zoom);
    }

    // Clear existing markers
    map.eachLayer(layer => {
      if (layer instanceof L.Marker) {
        map.removeLayer(layer);
      }
    });

    properties.forEach(property => {
      if (property.latitude && property.longitude) {
        const getMarkerColor = (score) => {
          if (!score) return '#6B7280';
          if (score >= 85) return '#22c55e';
          if (score >= 70) return '#16a34a';
          if (score >= 55) return '#ca8a04';
          if (score >= 40) return '#ea580c';
          return '#dc2626';
        };

        const markerHtml = `
          <div style="background-color: ${getMarkerColor(property.score)}; color: white; border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">
            ${property.score ? Math.round(property.score) : '?'}
          </div>
        `;

        const icon = L.divIcon({
          html: markerHtml,
          className: 'custom-marker',
          iconSize: [32, 32],
          iconAnchor: [16, 16]
        });

        const marker = L.marker([property.latitude, property.longitude], { icon }).addTo(map);

        const priceStr = typeof property.price === 'number' ? property.price.toLocaleString() : '0';
        const sqftStr = typeof property.sqft === 'number' ? property.sqft.toLocaleString() : '0';
        const popupContent = `
          <div>
            <strong>${escapeHtml(property.address)}</strong><br/>
            <span>${escapeHtml(property.city)}, ${escapeHtml(property.state)}</span><br/>
            <span>$${escapeHtml(priceStr)}</span><br/>
            <span>${escapeHtml(String(property.bedrooms))} bd | ${escapeHtml(String(property.bathrooms))} ba | ${escapeHtml(sqftStr)} sqft</span><br/>
            ${clickable ? `<a href="/property/${escapeHtml(String(property._id))}">View Details</a>` : ''}
          </div>
        `;
        marker.bindPopup(popupContent);
      }
    });

    if (!center && properties.length > 0) {
      const validProperties = properties.filter(p => p.latitude && p.longitude);
      if (validProperties.length > 0) {
        const bounds = validProperties.map(p => [p.latitude, p.longitude]);
        map.fitBounds(bounds);
      }
    }
  }, [properties, center, zoom, clickable]);

  return <div ref={mapRef} style={{ height, width: '100%' }} className="rounded-lg overflow-hidden" />;
};

export default MapView;
