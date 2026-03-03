import React, { useState } from 'react';

const PropertyGallery = ({ images }) => {
  const [selectedIndex, setSelectedIndex] = useState(0);

  if (!images || images.length === 0) {
    return null;
  }

  return (
    <div className="mt-4">
      <div className="rounded-lg overflow-hidden mb-2">
        <img
          src={images[selectedIndex]}
          alt={`Property view ${selectedIndex + 1}`}
          className="w-full h-64 object-cover"
        />
      </div>
      {images.length > 1 && (
        <div className="flex space-x-2 overflow-x-auto pb-2">
          {images.map((image, index) => (
            <button
              key={index}
              onClick={() => setSelectedIndex(index)}
              className={`flex-shrink-0 rounded overflow-hidden border-2 ${
                index === selectedIndex ? 'border-blue-500' : 'border-transparent'
              }`}
            >
              <img
                src={image}
                alt={`Thumbnail ${index + 1}`}
                className="w-16 h-16 object-cover"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default PropertyGallery;
