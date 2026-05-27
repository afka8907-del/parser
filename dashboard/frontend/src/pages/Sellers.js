import React, { useEffect, useState } from 'react';
import { Users, Star, Shield, AlertTriangle, Smartphone } from 'lucide-react';
import { getSellers } from '../services/api';
import { formatDate } from '../utils/formatters';

function Sellers() {
  const [sellers, setSellers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, trusted, flagged

  useEffect(() => {
    fetchSellers();
  }, [filter]);

  const fetchSellers = async () => {
    try {
      setLoading(true);
      const params = {};
      if (filter === 'trusted') params.is_trusted = true;
      
      const response = await getSellers(params);
      let data = response.data;
      
      if (filter === 'flagged') {
        data = data.filter(s => s.is_blacklisted || s.reputation_score < 3);
      }
      
      setSellers(data);
    } catch (error) {
      console.error('Error fetching sellers:', error);
    } finally {
      setLoading(false);
    }
  };

  const getReputationBadge = (score) => {
    if (score >= 4.5) return { color: 'bg-success/20 text-success', label: 'Excellent' };
    if (score >= 3.5) return { color: 'bg-accent/20 text-accent', label: 'Good' };
    if (score >= 2.5) return { color: 'bg-warning/20 text-warning', label: 'Average' };
    return { color: 'bg-danger/20 text-danger', label: 'Poor' };
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Sellers</h1>
          <p className="text-gray-400 mt-1">Seller reputation and activity analysis</p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2">
        {[
          { id: 'all', label: 'All Sellers' },
          { id: 'trusted', label: 'Trusted' },
          { id: 'flagged', label: 'Flagged' },
        ].map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              filter === f.id 
                ? 'bg-accent text-white' 
                : 'bg-dark-card text-gray-400 hover:text-white border border-dark-border'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Sellers Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sellers.map((seller) => {
            const rep = getReputationBadge(seller.reputation_score);
            
            return (
              <div 
                key={seller.id}
                className={`bg-dark-card rounded-xl border ${
                  seller.is_blacklisted ? 'border-danger' : 
                  seller.is_trusted ? 'border-success' : 'border-dark-border'
                } overflow-hidden`}
              >
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-dark-bg rounded-full flex items-center justify-center">
                        <Users size={24} className="text-gray-400" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-white">{seller.name}</h3>
                        <p className="text-sm text-gray-400">{seller.location || 'No location'}</p>
                      </div>
                    </div>
                    
                    <div className="flex flex-col items-end gap-1">
                      {seller.is_trusted && (
                        <span className="px-2 py-1 bg-success/20 text-success text-xs rounded-full flex items-center gap-1">
                          <Shield size={12} />
                          Trusted
                        </span>
                      )}
                      {seller.is_blacklisted && (
                        <span className="px-2 py-1 bg-danger/20 text-danger text-xs rounded-full flex items-center gap-1">
                          <AlertTriangle size={12} />
                          Blacklisted
                        </span>
                      )}
                      {seller.is_reseller && (
                        <span className="px-2 py-1 bg-warning/20 text-warning text-xs rounded-full">
                          Reseller
                        </span>
                      )}
                    </div>
                  </div>
                  
                  {/* Stats */}
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div className="text-center p-3 bg-dark-bg rounded-lg">
                      <p className="text-lg font-bold text-white">{seller.total_listings}</p>
                      <p className="text-xs text-gray-400">Total</p>
                    </div>
                    <div className="text-center p-3 bg-dark-bg rounded-lg">
                      <p className="text-lg font-bold text-accent">{seller.active_listings}</p>
                      <p className="text-xs text-gray-400">Active</p>
                    </div>
                    <div className="text-center p-3 bg-dark-bg rounded-lg">
                      <p className="text-lg font-bold text-success">{seller.sold_listings}</p>
                      <p className="text-xs text-gray-400">Sold</p>
                    </div>
                  </div>
                  
                  {/* Reputation */}
                  <div className="flex items-center justify-between p-3 bg-dark-bg rounded-lg">
                    <div className="flex items-center gap-2">
                      <Star size={16} className="text-warning" />
                      <span className="text-sm text-gray-400">Reputation</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${rep.color}`}>
                        {rep.label}
                      </span>
                      <span className="text-white font-semibold">{seller.reputation_score.toFixed(1)}/5</span>
                    </div>
                  </div>
                  
                  {/* Activity */}
                  <div className="mt-4 pt-4 border-t border-dark-border space-y-2 text-sm">
                    <div className="flex justify-between text-gray-400">
                      <span>First seen:</span>
                      <span className="text-white">{formatDate(seller.first_seen)}</span>
                    </div>
                    <div className="flex justify-between text-gray-400">
                      <span>Last seen:</span>
                      <span className="text-white">{formatDate(seller.last_seen)}</span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
      
      {!loading && sellers.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-400 text-lg">No sellers found in this category</p>
        </div>
      )}
    </div>
  );
}

export default Sellers;
