import React, { useEffect, useState } from 'react';
import { Bell, CheckCircle, Clock, ExternalLink, Filter } from 'lucide-react';
import { getAlerts } from '../services/api';
import { formatDate, formatPrice } from '../utils/formatters';

function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchAlerts();
  }, [filter]);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      const params = {};
      if (filter === 'sent') params.sent_only = true;
      if (filter !== 'all' && filter !== 'sent') params.alert_type = filter;
      
      const response = await getAlerts(params);
      setAlerts(response.data);
    } catch (error) {
      console.error('Error fetching alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  const getAlertIcon = (type) => {
    switch (type) {
      case 'new_deal':
        return <span className="text-success text-2xl">🔥</span>;
      case 'price_drop':
        return <span className="text-accent text-2xl">📉</span>;
      case 'urgent_sale':
        return <span className="text-warning text-2xl">⚡</span>;
      default:
        return <Bell size={24} className="text-gray-400" />;
    }
  };

  const getAlertLabel = (type) => {
    switch (type) {
      case 'new_deal':
        return { text: 'New Deal', color: 'bg-success/20 text-success' };
      case 'price_drop':
        return { text: 'Price Drop', color: 'bg-accent/20 text-accent' };
      case 'urgent_sale':
        return { text: 'Urgent', color: 'bg-warning/20 text-warning' };
      default:
        return { text: type, color: 'bg-gray-700 text-gray-300' };
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Alerts</h1>
          <p className="text-gray-400 mt-1">Deal notifications and market alerts</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {[
          { id: 'all', label: 'All Alerts' },
          { id: 'new_deal', label: '🔥 Deals' },
          { id: 'price_drop', label: '📉 Price Drops' },
          { id: 'sent', label: '✓ Sent to Telegram' },
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

      {/* Alerts List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
        </div>
      ) : (
        <div className="space-y-4">
          {alerts.map((alert) => {
            const label = getAlertLabel(alert.alert_type);
            
            return (
              <div 
                key={alert.id}
                className={`bg-dark-card rounded-xl border ${
                  alert.sent_to_telegram ? 'border-success/30' : 'border-dark-border'
                } overflow-hidden`}
              >
                <div className="p-6">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-12 h-12 bg-dark-bg rounded-lg flex items-center justify-center">
                      {getAlertIcon(alert.alert_type)}
                    </div>
                    
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${label.color}`}>
                          {label.text}
                        </span>
                        
                        {alert.sent_to_telegram && (
                          <span className="px-2 py-1 bg-success/20 text-success text-xs rounded-full flex items-center gap-1">
                            <CheckCircle size={12} />
                            Sent
                          </span>
                        )}
                        
                        <span className="text-gray-500 text-sm flex items-center gap-1">
                          <Clock size={12} />
                          {formatDate(alert.created_at)}
                        </span>
                      </div>
                      
                      <div 
                        className="prose prose-invert max-w-none"
                        dangerouslySetInnerHTML={{ __html: alert.message }}
                      />
                      
                      {alert.profit_estimate && (
                        <div className="mt-3 flex items-center gap-2">
                          <span className="text-gray-400 text-sm">Est. Profit:</span>
                          <span className="text-success font-semibold">
                            +{formatPrice(alert.profit_estimate)}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
      
      {!loading && alerts.length === 0 && (
        <div className="text-center py-12">
          <Bell size={48} className="text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400 text-lg">No alerts found</p>
          <p className="text-gray-500 text-sm mt-2">New deals and price drops will appear here</p>
        </div>
      )}
    </div>
  );
}

export default Alerts;
