import React from 'react';
import { Settings as SettingsIcon, Database, RefreshCw, Clock } from 'lucide-react';

const Settings: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <h1 className="text-3xl font-bold text-gray-900">Settings</h1>

      {/* Collection Settings */}
      <div className="card">
        <div className="flex items-center mb-4">
          <Clock className="h-6 w-6 text-primary-500 mr-3" />
          <h2 className="text-xl font-semibold text-gray-900">Data Collection</h2>
        </div>
        <div className="space-y-4">
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Current Status</h3>
            <div className="bg-green-50 border border-green-200 rounded-md p-3">
              <p className="text-green-800">Collection is active</p>
              <p className="text-sm text-green-600 mt-1">
                Last data point: {new Date().toLocaleString()}
              </p>
            </div>
          </div>
          
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Collection Interval</h3>
            <p className="text-gray-600">Data is collected every 10 seconds</p>
          </div>
        </div>
      </div>

      {/* Database Settings */}
      <div className="card">
        <div className="flex items-center mb-4">
          <Database className="h-6 w-6 text-primary-500 mr-3" />
          <h2 className="text-xl font-semibold text-gray-900">Database</h2>
        </div>
        <div className="space-y-4">
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Database Location</h3>
            <code className="bg-gray-100 px-2 py-1 rounded text-sm">
              data/wellbeing.db
            </code>
          </div>
          
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Storage Usage</h3>
            <p className="text-gray-600">Database size information will be displayed here</p>
          </div>
        </div>
      </div>

      {/* Processing Settings */}
      <div className="card">
        <div className="flex items-center mb-4">
          <RefreshCw className="h-6 w-6 text-primary-500 mr-3" />
          <h2 className="text-xl font-semibold text-gray-900">Data Processing</h2>
        </div>
        <div className="space-y-4">
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Processing Status</h3>
            <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
              <p className="text-blue-800">Processing is active</p>
              <p className="text-sm text-blue-600 mt-1">
                Data is processed every 5 minutes
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* API Configuration */}
      <div className="card">
        <div className="flex items-center mb-4">
          <SettingsIcon className="h-6 w-6 text-primary-500 mr-3" />
          <h2 className="text-xl font-semibold text-gray-900">API Configuration</h2>
        </div>
        <div className="space-y-4">
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Backend URL</h3>
            <code className="bg-gray-100 px-2 py-1 rounded text-sm">
              http://localhost:8847
            </code>
          </div>
          
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Frontend URL</h3>
            <code className="bg-gray-100 px-2 py-1 rounded text-sm">
              http://localhost:3847
            </code>
          </div>
        </div>
      </div>

      {/* System Information */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">System Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Platform</h3>
            <p className="text-gray-600">Linux (Wayland/Hyprland)</p>
          </div>
          
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Version</h3>
            <p className="text-gray-600">1.0.0</p>
          </div>
          
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Data Retention</h3>
            <p className="text-gray-600">Unlimited (manual cleanup required)</p>
          </div>
          
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Privacy</h3>
            <p className="text-gray-600">All data stored locally</p>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Actions</h2>
        <div className="space-y-3">
          <button className="btn-primary mr-3">
            Export Data
          </button>
          <button className="btn-secondary mr-3">
            Clear Old Data
          </button>
          <button className="btn-secondary">
            Reset Categories
          </button>
        </div>
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          <p className="text-yellow-800 text-sm">
            <strong>Note:</strong> These actions are not yet implemented. 
            They would typically handle data export, cleanup, and configuration reset.
          </p>
        </div>
      </div>

      {/* Help */}
      <div className="card bg-gray-50">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Help & Documentation</h2>
        <div className="space-y-2">
          <p className="text-gray-700">
            <strong>Starting the Collector:</strong> Run <code>python collector/collector.py</code>
          </p>
          <p className="text-gray-700">
            <strong>Starting the Processor:</strong> Run <code>python processor/processor.py</code>
          </p>
          <p className="text-gray-700">
            <strong>Starting the API:</strong> Run <code>python backend/main.py</code>
          </p>
          <p className="text-gray-700">
            <strong>Starting the Frontend:</strong> Run <code>npm run dev</code> in the frontend directory
          </p>
        </div>
      </div>
    </div>
  );
};

export default Settings;
