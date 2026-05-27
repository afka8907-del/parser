import React, { useEffect, useState } from 'react';
import { DollarSign, TrendingUp, AlertTriangle, CheckCircle, ExternalLink } from 'lucide-react';
import { getDeals } from '../services/api';
import { formatPrice, getScoreColor, getScoreBg } from '../utils/formatters';

function Deals() {
  const [deals, setDeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [minProfit, setMinProfit] = useState(1000);

  useEffect(() => {
    fetchDeals();
  }, [minProfit]);

  const fetchDeals = async () => {
    try {
      setLoading(true);
      const response = await getDeals({ min_profit: minProfit, limit: 50 });
      setDeals(response.data);
    } catch (error) {
      console.error('Error fetching deals:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">🔥 Hot Deals</h1>
          <p className="text-gray-400 mt-1">Best profit opportunities sorted by potential profit</p>
        </div>
        
        <div className="flex items-center gap-4">
          <label className="text-sm text-gray-400">Min Profit:</label>
          <select
            value={minProfit}
            onChange={(e) => setMinProfit(Number(e.target.value))}
            className="px-4 py-2 bg-dark-card border border-dark-border rounded-lg text-white focus:border-accent focus:outline-none"
          >
            <option value={500}>500 MDL</option>
            <option value={1000}>1000 MDL</option>
            <option value={2000}>2000 MDL</option>
            <option value={5000}>5000 MDL</option>
          </select>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-dark-card rounded-xl p-6 border border-dark-border">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-success/20 rounded-lg">
              <DollarSign size={24} className="text-success" />
            </div>
            <div>
              <p className="text-gray-400 text-sm">Total Deals</p>
              <p className="text-2xl font-bold text-white">{deals.length}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-dark-card rounded-xl p-6 border border-dark-border">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-accent/20 rounded-lg">
              <TrendingUp size={24} className="text-accent" />
            </div>
            <div>
              <p className="text-gray-400 text-sm">Avg Margin</p>
              <p className="text-2xl font-bold text-white">
                {deals.length > 0 
                  ? Math.round(deals.reduce((acc, d) => acc + d.profit_margin, 0) / deals.length)
                  : 0}%
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-dark-card rounded-xl p-6 border border-dark-border">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-warning/20 rounded-lg">
              <AlertTriangle size={24} className="text-warning" />
            </div>
            <div>
              <p className="text-gray-400 text-sm">Avg Risk Score</p>
              <p className="text-2xl font-bold text-white">
                {deals.length > 0 
                  ? Math.round(deals.reduce((acc, d) => acc + d.risk_score, 0) / deals.length)
                  : 0}/100
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Deals List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
        </div>
      ) : (
        <div className="space-y-4">
          {deals.map((deal, index) => (
            <div 
              key={deal.listing.id}
              className="bg-dark-card rounded-xl border border-dark-border overflow-hidden"
            >
              <div className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    <div className={`
                      w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold
                      ${getScoreBg(deal.score)}
                      ${getScoreColor(deal.score)}
                    `}>
                      #{index + 1}
                    </div>
                    
                    <div>
                      <h3 className="text-xl font-semibold text-white">
                        {deal.listing.model}
                        {deal.listing.storage_gb && ` ${deal.listing.storage_gb}GB`}
                      </h3>
                      <p className="text-gray-400 mt-1">{deal.listing.location}</p>
                      
                      <div className="flex items-center gap-4 mt-3">
                        <span className={`
                          px-3 py-1 rounded-full text-sm font-medium
                          ${deal.risk_score < 30 ? 'bg-success/20 text-success' : 
                            deal.risk_score < 60 ? 'bg-warning/20 text-warning' : 
                            'bg-danger/20 text-danger'}
                        `}>
                          Risk: {deal.risk_score}/100
                        </span>
                        
                        {deal.listing.battery_health && (
                          <span className="px-3 py-1 bg-dark-bg rounded-full text-sm text-gray-400">
                            🔋 {deal.listing.battery_health}%
                          </span>
                        )}
                        
                        {deal.resale_speed_score > 70 && (
                          <span className="px-3 py-1 bg-accent/20 rounded-full text-sm text-accent">
                            Fast Sale
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <p className="text-3xl font-bold text-success">
                      +{formatPrice(deal.profit)}
                    </p>
                    <p className="text-gray-400 text-sm mt-1">
                      {deal.profit_margin}% margin
                    </p>
                  </div>
                </div>
                
                {/* Price Breakdown */}
                <div className="mt-6 pt-6 border-t border-dark-border">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-sm text-gray-400">Buy Price</p>
                      <p className="text-lg font-semibold text-white">
                        {formatPrice(deal.current_price)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-400">Market Median</p>
                      <p className="text-lg font-semibold text-white">
                        {formatPrice(deal.market_median)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-400">Est. Resale</p>
                      <p className="text-lg font-semibold text-success">
                        {formatPrice(deal.estimated_resale)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-400">Est. Profit</p>
                      <p className="text-lg font-semibold text-success">
                        {formatPrice(deal.estimated_profit)}
                      </p>
                    </div>
                  </div>
                </div>
                
                {/* Scores */}
                <div className="mt-6 flex flex-wrap gap-4">
                  <div className="flex items-center gap-2">
                    <CheckCircle size={16} className="text-success" />
                    <span className="text-sm text-gray-400">
                      Profit Score: <span className="text-white font-medium">{deal.profit_score}/100</span>
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle size={16} className="text-accent" />
                    <span className="text-sm text-gray-400">
                      Demand: <span className="text-white font-medium">{deal.demand_score}/100</span>
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle size={16} className="text-warning" />
                    <span className="text-sm text-gray-400">
                      Resale Speed: <span className="text-white font-medium">{deal.resale_speed_score}/100</span>
                    </span>
                  </div>
                </div>
                
                {/* Issues */}
                {(deal.listing.face_id_issue || deal.listing.icloud_locked || 
                  deal.listing.broken_display || deal.listing.replaced_parts) && (
                  <div className="mt-4 p-4 bg-warning/10 rounded-lg border border-warning/30">
                    <p className="text-warning font-medium mb-2">⚠️ Issues Detected:</p>
                    <div className="flex flex-wrap gap-2">
                      {deal.listing.face_id_issue && (
                        <span className="px-2 py-1 bg-warning/20 text-warning text-sm rounded">Face ID Issue</span>
                      )}
                      {deal.listing.icloud_locked && (
                        <span className="px-2 py-1 bg-danger/20 text-danger text-sm rounded">iCloud Locked</span>
                      )}
                      {deal.listing.broken_display && (
                        <span className="px-2 py-1 bg-warning/20 text-warning text-sm rounded">Broken Display</span>
                      )}
                      {deal.listing.replaced_parts && (
                        <span className="px-2 py-1 bg-warning/20 text-warning text-sm rounded">Replaced Parts</span>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Recommendation */}
                <div className="mt-4">
                  <p className={`font-semibold ${
                    deal.score >= 80 ? 'text-success' : 
                    deal.score >= 60 ? 'text-accent' : 'text-warning'
                  }`}>
                    {deal.recommendation}
                  </p>
                </div>
                
                {/* Actions */}
                <div className="mt-6 flex items-center justify-end gap-4">
                  <a 
                    href={deal.listing.listing_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-6 py-3 bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors font-medium"
                  >
                    View on 999.md
                    <ExternalLink size={18} />
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {!loading && deals.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-400 text-lg">No profitable deals found with current criteria</p>
          <p className="text-gray-500 text-sm mt-2">Try lowering the minimum profit threshold</p>
        </div>
      )}
    </div>
  );
}

export default Deals;
