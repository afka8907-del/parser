import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  TrendingUp, 
  DollarSign, 
  Search, 
  Users, 
  Bell,
  Menu,
  X
} from 'lucide-react';
import { useState } from 'react';

import Dashboard from './pages/Dashboard';
import Listings from './pages/Listings';
import Deals from './pages/Deals';
import Market from './pages/Market';
import Sellers from './pages/Sellers';
import Alerts from './pages/Alerts';

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/listings', icon: Search, label: 'Listings' },
    { path: '/deals', icon: DollarSign, label: 'Deals' },
    { path: '/market', icon: TrendingUp, label: 'Market' },
    { path: '/sellers', icon: Users, label: 'Sellers' },
    { path: '/alerts', icon: Bell, label: 'Alerts' },
  ];

  return (
    <Router>
      <div className="flex h-screen bg-dark-bg">
        {/* Mobile sidebar overlay */}
        {sidebarOpen && (
          <div 
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Sidebar */}
        <aside className={`
          fixed lg:static inset-y-0 left-0 z-50
          w-64 bg-dark-card border-r border-dark-border
          transform transition-transform duration-200 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}>
          <div className="flex items-center justify-between p-6 border-b border-dark-border">
            <h1 className="text-xl font-bold text-white">
              iPhone Intel
            </h1>
            <button 
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-gray-400 hover:text-white"
            >
              <X size={24} />
            </button>
          </div>

          <nav className="p-4 space-y-2">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) => `
                  flex items-center gap-3 px-4 py-3 rounded-lg
                  transition-colors duration-200
                  ${isActive 
                    ? 'bg-accent text-white' 
                    : 'text-gray-400 hover:bg-dark-border hover:text-white'
                  }
                `}
              >
                <item.icon size={20} />
                <span className="font-medium">{item.label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-dark-border">
            <div className="text-sm text-gray-500">
              <p>Parser Status: <span className="text-success">● Active</span></p>
              <p className="mt-1">Last run: 2 min ago</p>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Header */}
          <header className="flex items-center justify-between px-6 py-4 bg-dark-card border-b border-dark-border lg:hidden">
            <button 
              onClick={() => setSidebarOpen(true)}
              className="text-gray-400 hover:text-white"
            >
              <Menu size={24} />
            </button>
            <h1 className="text-lg font-semibold text-white">iPhone Intel</h1>
            <div className="w-6" /> {/* Spacer for alignment */}
          </header>

          {/* Page content */}
          <div className="flex-1 overflow-auto p-6">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/listings" element={<Listings />} />
              <Route path="/deals" element={<Deals />} />
              <Route path="/market" element={<Market />} />
              <Route path="/sellers" element={<Sellers />} />
              <Route path="/alerts" element={<Alerts />} />
            </Routes>
          </div>
        </main>
      </div>
    </Router>
  );
}

export default App;
