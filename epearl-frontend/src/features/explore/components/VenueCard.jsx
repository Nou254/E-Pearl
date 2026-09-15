import React from 'react';
import { Link } from 'react-router-dom';

const VenueCard = ({ venue }) => {
  return (
    <Link to={`/venue/${venue.id}`} className="block">
      <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-300">
        <img
          src={venue.cover_image_url || 'https://via.placeholder.com/400x200?text=No+Image'}
          alt={venue.business_name}
          className="w-full h-48 object-cover"
        />
        <div className="p-4">
          <h3 className="text-lg font-semibold text-gray-800">{venue.business_name}</h3>
          <p className="text-sm text-gray-600 mt-1 line-clamp-2">{venue.description}</p>
          <div className="mt-2 flex items-center justify-between text-sm text-gray-500">
            <span>{venue.subscription_tier}</span>
            <span> {venue.gps_coordinates || 'Location not set'}</span>
          </div>
        </div>
      </div>
    </Link>
  );
};

export default VenueCard;