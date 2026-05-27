import React, { useEffect, useState } from 'react';
import { Search, Filter, ExternalLink, Battery, MapPin, AlertTriangle } from 'lucide-react';
import { getListings, getModels } from '../services/api';
import { formatPrice, formatDate } from '../utils/formatters';

function Listings() {
  const [listings, setListings] = useState([]);
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    model: '',
    min_price: '',
    max_price: '',
    is_underpriced: false,
  });

  useEffect(() => {
    fetchListings();
    fetchModels();
  }, []);

  const fetchListings = async () => {
    try {
      setLoading(true);
      const params = {};
      if (filters.model) params.model = filters.model;
      if (filters.min_price) params.min_price = filters.min_price;
      if (filters.max_price) params.max_price = filters.max_price;
      if (filters.is_underpriced) params.is_underpriced = true;
      
      const response = await getListings(params);
      setListings(response.data);
    } catch (error) {
      console.error('Error fetching listings:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchModels = async () => {
    try {
      const response = await getModels();
      setModels(response.data);
    } catch (error) {
      console.error('Error fetching models:', error);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const applyFilters = () => {
    fetchListings();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Listings</h1>
          <p className="text-gray-400 mt-1">Browse all iPhone listings from 999.md</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-dark-card rounded-xl p-6 border border-dark-border">
        <div className="flex items-center gap-2 mb-4">
          <Filter size={20} className="text-gray-400" />
          <h2 className="text-lg font-semibold text-white">Filters</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Model</label>
            <select
              value={filters.model}
              onChange={(e) => handleFilterChange('model', e.target.value)}
              className="w-full px-4 py-2 bg-dark-bg border border-dark-border rounded-lg text-white focus:border-accent focus:outline-none"
            >
              <option value="">All Models</option>
              {models.map((m) => (
                <option key={m.model} value={m.model}>{m.model} ({m.count})</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm text-gray-400 mb-2">Min Price</label>
            <input
              type="number"
              value={filters.min_price}
              onChange={(e) => handleFilterChange('min_price', e.target.value)}
              placeholder="0"
              className="w-full px-4 py-2 bg-dark-bg border border-dark-border rounded-lg text-white focus:border-accent focus:outline-none"
            />
          </div>
          
          <div>
            <label className="block text-sm text-gray-400 mb-2">Max Price</label>
            <input
              type="number"
              value={filters.max_price}
              onChange={(e) => handleFilterChange('max_price', e.target.value)}
              placeholder="50000"
              className="w-full px-4 py-2 bg-dark-bg border border-dark-border rounded-lg text-white focus:border-accent focus:outline-none"
            />
          </div>
          
          <div className="flex items-end">
            <button
              onClick={applyFilters}
              className="w-full px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors flex items-center justify-center gap-2"
            >
              <Search size={18} />
              Apply Filters
            </button>
          </div>
        </div>
        
        <div className="mt-4 flex items-center gap-2">
          <input
            type="checkbox"
            id="underpriced"
            checked={filters.is_underpriced}
            onChange={(e) => handleFilterChange('is_underpriced', e.target.checked)}
            className="w-4 h-4 rounded border-dark-border"
          />
          <label htmlFor="underpriced" className="text-sm text-gray-400">
            Show only underpriced deals
          </label>
        </div>
      </div>

      {/* Listings Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {listings.map((listing) => (
            <div 
              key={listing.id} 
              className={`bg-dark-card rounded-xl border ${listing.is_underpriced ? 'border-success' : 'border-dark-border'} overflow-hidden hover:border-accent transition-colors`}
            >
              {listing.images && listing.images[0] && (
                <div className="h-48 overflow-hidden bg-dark-bg">
                  <img 
                    src={listing.images[0]} 
                    alt={listing.title}
                    className="w-full h-full object-cover hover:scale-105 transition-transform"
                  />
                </div>
              )}
              
              <div className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-white line-clamp-2">{listing.title}</h3>
                  {listing.is_underpriced && (
                    <span className="px-2 py-1 bg-success/20 text-success text-xs rounded-full font-medium">
                      DEAL
                    </span>
                  )}
                </div>
                
                <p className="text-2xl font-bold text-accent mb-3">
                  {formatPrice(listing.price, listing.currency)}
                </p>
                
                <div className="space-y-2 text-sm">
                  {listing.battery_health && (
                    <div className="flex items-center gap-2 text-gray-400">
                      <Battery size={14} />
                      <span>{listing.battery_health}% battery</span>
                    </div>
                  )}
                  
                  {listing.location && (
                    <div className="flex items-center gap-2 text-gray-400">
                      <MapPin size={14} />
                      <span>{listing.location}</span>
                    </div>
                  )}
                  
                  {(listing.face_id_issue || listing.icloud_locked || listing.broken_display) && (
                    <div className="flex items-center gap-2 text-warning">
                      <AlertTriangle size={14} />
                      <span>Issues detected</span>
                    </div>
                  )}
                </div>
                
                {listing.estimated_profit && (
                  <div className="mt-3 pt-3 border-t border-dark-border">
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-400">Est. profit:</span>
                      <span className="text-success font-semibold">
                        +{formatPrice(listing.estimated_profit)}
                      </span>
                    </div>
                  </div>
                )}
                
                <div className="mt-4 pt-3 border-t border-dark-border flex items-center justify-between">
                  <span className="text-xs text-gray-500">
                    {formatDate(listing.scraped_at)}
                  </span>
                  <a 
                    href={listing.listing_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-accent hover:text-accent-hover text-sm font-medium"
                  >
                    View <ExternalLink size={14} />
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {!loading && listings.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-400 text-lg">No listings found matching your criteria</p>
        </div>
      )}
    </div>
  );
}

export default Listings;
