import React, { useEffect, useState } from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  LineChart,
  Line,
  Legend
} from 'recharts';
import { TrendingUp, DollarSign, Package } from 'lucide-react';
import { getMarketStats, getTrends } from '../services/api';
import { formatPrice } from '../utils/formatters';

function Market() {
  const [stats, setStats] = useState([]);
  const [trends, setTrends] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedModel, setSelectedModel] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statsRes, trendsRes] = await Promise.all([
        getMarketStats(),
        getTrends(30),
      ]);
      setStats(statsRes.data);
      setTrends(trendsRes.data);
    } catch (error) {
      console.error('Error fetching market data:', error);
    } finally {
      setLoading(false);
    }
  };

  const chartData = stats.map(s => ({
    name: `${s.model} ${s.storage_gb || ''}GB`,
    avgPrice: s.avg_price,
    medianPrice: s.median_price,
    minPrice: s.min_price,
    maxPrice: s.max_price,
    listings: s.total_listings,
    model: s.model,
    storage: s.storage_gb,
  }));

  const topModels = [...stats]
    .sort((a, b) => b.total_listings - a.total_listings)
    .slice(0, 10);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Market Analysis</h1>
          <p className="text-gray-400 mt-1">Price trends and market statistics</p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-dark-card rounded-xl p-6 border border-dark-border">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-accent/20 rounded-lg">
              <Package size={24} className="text-accent" />
            </div>
            <div>
              <p className="text-gray-400 text-sm">Model Variants</p>
              <p className="text-2xl font-bold text-white">{stats.length}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-dark-card rounded-xl p-6 border border-dark-border">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-success/20 rounded-lg">
              <DollarSign size={24} className="text-success" />
            </div>
            <div>
              <p className="text-gray-400 text-sm">Avg Market Price</p>
              <p className="text-2xl font-bold text-white">
                {stats.length > 0 
                  ? formatPrice(stats.reduce((acc, s) => acc + s.avg_price, 0) / stats.length)
                  : '0 MDL'
                }
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-dark-card rounded-xl p-6 border border-dark-border">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-warning/20 rounded-lg">
              <TrendingUp size={24} className="text-warning" />
            </div>
            <div>
              <p className="text-gray-400 text-sm">Total Listings</p>
              <p className="text-2xl font-bold text-white">
                {stats.reduce((acc, s) => acc + s.total_listings, 0).toLocaleString()}
              </p>
            </div>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
        </div>
      ) : (
        <>
          {/* Price Chart */}
          <div className="bg-dark-card rounded-xl border border-dark-border p-6">
            <h2 className="text-lg font-semibold text-white mb-6">Average Prices by Model</h2>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 100 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis 
                    type="number" 
                    tick={{ fill: '#94a3b8' }}
                    tickFormatter={(value) => `${value/1000}k`}
                  />
                  <YAxis 
                    dataKey="name" 
                    type="category" 
                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                    width={120}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1e293b', 
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#fff'
                    }}
                    formatter={(value) => formatPrice(value)}
                  />
                  <Legend />
                  <Bar dataKey="avgPrice" name="Average" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                  <Bar dataKey="medianPrice" name="Median" fill="#10b981" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Top Models Table */}
          <div className="bg-dark-card rounded-xl border border-dark-border overflow-hidden">
            <div className="px-6 py-4 border-b border-dark-border">
              <h2 className="text-lg font-semibold text-white">Top Models by Volume</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-dark-bg">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                      Model
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                      Storage
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                      Avg Price
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                      Median Price
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                      Price Range
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                      Listings
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-border">
                  {topModels.map((stat, index) => (
                    <tr key={index} className="hover:bg-dark-bg/50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">
                        {stat.model}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                        {stat.storage_gb ? `${stat.storage_gb}GB` : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-white">
                        {formatPrice(stat.avg_price)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-white">
                        {formatPrice(stat.median_price)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-400">
                        {formatPrice(stat.min_price)} - {formatPrice(stat.max_price)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                        <span className="px-2 py-1 bg-accent/20 text-accent rounded-full text-xs font-medium">
                          {stat.total_listings}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Market Insights */}
          {trends && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-dark-card rounded-xl border border-dark-border p-6">
                <h3 className="text-lg font-semibold text-white mb-4">30-Day Activity</h3>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400">New Listings</span>
                    <span className="font-semibold text-white">{trends.new_listings}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400">Sold/Removed</span>
                    <span className="font-semibold text-success">{trends.sold_listings}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400">Market Velocity</span>
                    <span className="font-semibold text-white">{trends.market_velocity.toFixed(1)} items/day</span>
                  </div>
                </div>
              </div>

              <div className="bg-dark-card rounded-xl border border-dark-border p-6">
                <h3 className="text-lg font-semibold text-white mb-4">Current Avg Prices</h3>
                <div className="space-y-3 max-h-64 overflow-y-auto">
                  {Object.entries(trends.current_avg_prices || {})
                    .slice(0, 10)
                    .map(([model, price]) => (
                      <div key={model} className="flex justify-between items-center">
                        <span className="text-gray-400 text-sm">{model}</span>
                        <span className="font-semibold text-white">{formatPrice(price)}</span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default Market;
