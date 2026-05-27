import React, { useEffect, useState } from 'react';
import { 
  TrendingUp, 
  DollarSign, 
  Users, 
  Smartphone,
  ArrowUp,
  ArrowDown,
  Activity
} from 'lucide-react';
import { getStats, getDeals, getTrends } from '../services/api';
import { formatPrice, formatNumber } from '../utils/formatters';

const StatCard = ({ title, value, icon: Icon, trend, trendValue, color }) => (
  <div className="bg-dark-card rounded-xl p-6 border border-dark-border">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-gray-400 text-sm font-medium">{title}</p>
        <h3 className="text-2xl font-bold text-white mt-2">{value}</h3>
        {trend && (
          <div className={`flex items-center gap-1 mt-2 text-sm ${trend === 'up' ? 'text-success' : 'text-danger'}`}>
            {trend === 'up' ? <ArrowUp size={16} /> : <ArrowDown size={16} />}
            <span>{trendValue}</span>
          </div>
        )}
      </div>
      <div className={`p-4 rounded-lg ${color}`}>
        <Icon size={24} className="text-white" />
      </div>
    </div>
  </div>
);

const RecentDealCard = ({ deal }) => (
  <div className="bg-dark-card rounded-lg p-4 border border-dark-border hover:border-accent transition-colors">
    <div className="flex items-start justify-between">
      <div>
        <h4 className="font-semibold text-white">{deal.listing.model}</h4>
        <p className="text-gray-400 text-sm mt-1">
          {deal.listing.storage_gb && `${deal.listing.storage_gb}GB`} • {deal.listing.location}
        </p>
      </div>
      <div className="text-right">
        <p className="text-success font-bold">+{formatPrice(deal.profit)}</p>
        <p className="text-gray-400 text-sm">{deal.profit_margin}% margin</p>
      </div>
    </div>
    <div className="mt-3 pt-3 border-t border-dark-border flex items-center justify-between">
      <div className="flex items-center gap-4 text-sm">
        <span className="text-gray-400">
          Buy: {formatPrice(deal.current_price)}
        </span>
        <span className="text-gray-400">
          Sell: {formatPrice(deal.estimated_resale)}
        </span>
      </div>
      <a 
        href={deal.listing.listing_url} 
        target="_blank" 
        rel="noopener noreferrer"
        className="text-accent hover:text-accent-hover text-sm font-medium"
      >
        View →
      </a>
    </div>
  </div>
);

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [deals, setDeals] = useState([]);
  const [trends, setTrends] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [statsRes, dealsRes, trendsRes] = await Promise.all([
          getStats(),
          getDeals({ limit: 5 }),
          getTrends(7),
        ]);
        
        setStats(statsRes.data);
        setDeals(dealsRes.data);
        setTrends(trendsRes.data);
        setError(null);
      } catch (err) {
        setError('Failed to load dashboard data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-danger/10 border border-danger/30 rounded-lg p-6 text-center">
        <p className="text-danger font-medium">{error}</p>
        <button 
          onClick={() => window.location.reload()}
          className="mt-4 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-400 mt-1">Overview of iPhone market and opportunities</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-2 px-4 py-2 bg-success/20 text-success rounded-lg text-sm font-medium">
            <Activity size={16} />
            Live
          </span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Active Listings"
          value={formatNumber(stats?.total_active_listings || 0)}
          icon={Smartphone}
          trend="up"
          trendValue={`+${stats?.new_listings_today || 0} today`}
          color="bg-blue-500/20"
        />
        <StatCard
          title="Profitable Deals"
          value={formatNumber(stats?.total_profitable_deals || 0)}
          icon={DollarSign}
          trend="up"
          trendValue="Active now"
          color="bg-success/20"
        />
        <StatCard
          title="Avg Price"
          value={formatPrice(stats?.average_price || 0)}
          icon={TrendingUp}
          color="bg-warning/20"
        />
        <StatCard
          title="Active Sellers"
          value={formatNumber(stats?.active_sellers || 0)}
          icon={Users}
          color="bg-purple-500/20"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Deals */}
        <div className="lg:col-span-2">
          <div className="bg-dark-card rounded-xl border border-dark-border">
            <div className="px-6 py-4 border-b border-dark-border flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">🔥 Hot Deals</h2>
              <a href="/deals" className="text-accent hover:text-accent-hover text-sm font-medium">
                View all →
              </a>
            </div>
            <div className="p-6 space-y-4">
              {deals.length > 0 ? (
                deals.map((deal, index) => (
                  <RecentDealCard key={deal.listing.id || index} deal={deal} />
                ))
              ) : (
                <p className="text-gray-400 text-center py-8">No profitable deals found</p>
              )}
            </div>
          </div>
        </div>

        {/* Side Panel */}
        <div className="space-y-6">
          {/* Market Trends */}
          <div className="bg-dark-card rounded-xl border border-dark-border p-6">
            <h2 className="text-lg font-semibold text-white mb-4">📈 Market Trends</h2>
            {trends && (
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">New listings (7d)</span>
                  <span className="font-semibold text-white">{trends.new_listings}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Sold (7d)</span>
                  <span className="font-semibold text-success">{trends.sold_listings}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Velocity</span>
                  <span className="font-semibold text-white">{trends.market_velocity.toFixed(1)}/day</span>
                </div>
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="bg-dark-card rounded-xl border border-dark-border p-6">
            <h2 className="text-lg font-semibold text-white mb-4">⚡ Quick Actions</h2>
            <div className="space-y-3">
              <a 
                href="/listings" 
                className="block w-full px-4 py-3 bg-dark-border hover:bg-accent/20 text-white rounded-lg transition-colors text-center"
              >
                Browse Listings
              </a>
              <a 
                href="/market" 
                className="block w-full px-4 py-3 bg-dark-border hover:bg-accent/20 text-white rounded-lg transition-colors text-center"
              >
                Market Analysis
              </a>
              <a 
                href="/sellers" 
                className="block w-full px-4 py-3 bg-dark-border hover:bg-accent/20 text-white rounded-lg transition-colors text-center"
              >
                Top Sellers
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
