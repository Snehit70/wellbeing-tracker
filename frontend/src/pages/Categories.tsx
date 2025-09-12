import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Save, X } from 'lucide-react';
import { LoadingSpinner, ErrorMessage, UsageChart } from '../components/Charts';
import { useCategories, updateAppCategory, removeAppFromCategory } from '../hooks/useApi';

interface CategoryEditProps {
  category: string;
  apps: string[];
  color: string;
  description: string;
  onUpdate: () => void;
}

const CategoryEdit: React.FC<CategoryEditProps> = ({ category, apps, color, description, onUpdate }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [newAppName, setNewAppName] = useState('');
  const [isAddingApp, setIsAddingApp] = useState(false);

  const handleAddApp = async () => {
    if (!newAppName.trim()) return;
    
    try {
      await updateAppCategory(newAppName.trim(), category);
      setNewAppName('');
      setIsAddingApp(false);
      onUpdate();
    } catch (error) {
      console.error('Failed to add app:', error);
    }
  };

  const handleRemoveApp = async (appName: string) => {
    try {
      await removeAppFromCategory(appName, category);
      onUpdate();
    } catch (error) {
      console.error('Failed to remove app:', error);
    }
  };

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          <div 
            className="w-4 h-4 rounded mr-3" 
            style={{ backgroundColor: color }}
          />
          <h3 className="text-lg font-semibold text-gray-900">{category}</h3>
        </div>
        <button
          onClick={() => setIsEditing(!isEditing)}
          className="text-gray-400 hover:text-gray-600"
        >
          <Edit2 className="h-4 w-4" />
        </button>
      </div>
      
      <p className="text-sm text-gray-600 mb-4">{description}</p>
      
      <div className="mb-4">
        <span className="text-sm font-medium text-gray-700">Apps ({apps.length}):</span>
      </div>
      
      <div className="space-y-2">
        {apps.map((app) => (
          <div key={app} className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-md">
            <span className="text-sm text-gray-900">{app}</span>
            {isEditing && (
              <button
                onClick={() => handleRemoveApp(app)}
                className="text-red-400 hover:text-red-600"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>
        ))}
        
        {isEditing && (
          <div className="mt-3">
            {!isAddingApp ? (
              <button
                onClick={() => setIsAddingApp(true)}
                className="flex items-center text-sm text-primary-600 hover:text-primary-700"
              >
                <Plus className="h-4 w-4 mr-1" />
                Add app
              </button>
            ) : (
              <div className="flex items-center space-x-2">
                <input
                  type="text"
                  value={newAppName}
                  onChange={(e) => setNewAppName(e.target.value)}
                  placeholder="App name"
                  className="input flex-1 text-sm"
                  onKeyPress={(e) => e.key === 'Enter' && handleAddApp()}
                />
                <button
                  onClick={handleAddApp}
                  className="text-green-600 hover:text-green-700"
                >
                  <Save className="h-4 w-4" />
                </button>
                <button
                  onClick={() => {
                    setIsAddingApp(false);
                    setNewAppName('');
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const Categories: React.FC = () => {
  const { data: categoriesData, loading, error, refetch } = useCategories();
  const [refreshKey, setRefreshKey] = useState(0);

  // Trigger refetch when refreshKey changes
  useEffect(() => {
    if (refreshKey > 0) {
      refetch();
    }
  }, [refreshKey, refetch]);

  const handleUpdate = () => {
    setRefreshKey(prev => prev + 1);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return <ErrorMessage message={error} retry={() => handleUpdate()} />;
  }

  if (!categoriesData) {
    return <ErrorMessage message="No categories data available" />;
  }

  const categories = Object.entries(categoriesData.categories);
  
  // Prepare data for visualization
  const categoryChartData = categories.map(([name, info]) => ({
    category: name,
    app_count: info.apps.length,
    color: info.color
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Categories</h1>
        <button 
          onClick={handleUpdate}
          className="btn-primary"
        >
          Refresh
        </button>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Total Categories</h3>
          <p className="text-3xl font-bold text-primary-600">{categories.length}</p>
        </div>
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Total Apps Mapped</h3>
          <p className="text-3xl font-bold text-primary-600">
            {categories.reduce((sum, [, info]) => sum + info.apps.length, 0)}
          </p>
        </div>
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Largest Category</h3>
          <p className="text-lg font-semibold text-gray-900">
            {categories.reduce((max, [name, info]) => 
              info.apps.length > (max.count || 0) ? { name, count: info.apps.length } : max, 
              { name: 'None', count: 0 }
            ).name}
          </p>
        </div>
      </div>

      {/* Category Distribution Chart */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Apps per Category</h2>
        <UsageChart
          data={categoryChartData}
          type="bar"
          height={300}
          dataKey="app_count"
          nameKey="category"
        />
      </div>

      {/* Categories Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {categories.map(([name, info]) => (
          <CategoryEdit
            key={name}
            category={name}
            apps={info.apps}
            color={info.color}
            description={info.description}
            onUpdate={handleUpdate}
          />
        ))}
      </div>

      {/* Instructions */}
      <div className="card bg-blue-50 border-blue-200">
        <h3 className="text-lg font-semibold text-blue-900 mb-2">How to use Categories</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• Click the edit icon on any category to manage its apps</li>
          <li>• Add new apps by typing the app name and clicking save</li>
          <li>• Remove apps by clicking the trash icon next to them</li>
          <li>• App names should match the process names from your system</li>
          <li>• Categories help organize your time tracking and create meaningful insights</li>
        </ul>
      </div>

      {/* Quick Add Section */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Add Common Apps</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { app: 'firefox', category: 'Browsing' },
            { app: 'chrome', category: 'Browsing' },
            { app: 'code', category: 'Work' },
            { app: 'terminal', category: 'System' },
            { app: 'spotify', category: 'Entertainment' },
            { app: 'discord', category: 'Communication' },
            { app: 'slack', category: 'Communication' },
            { app: 'notion', category: 'Productivity' },
          ].map(({ app, category }) => (
            <button
              key={`${app}-${category}`}
              onClick={() => {
                updateAppCategory(app, category).then(() => handleUpdate());
              }}
              className="btn-secondary text-xs"
            >
              Add {app} to {category}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Categories;
