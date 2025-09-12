import React, { useState } from 'react';
import { Clock, Monitor, TrendingUp, Calendar } from 'lucide-react';
import { StatCard, UsageChart, LoadingSpinner, ErrorMessage } from '../components/Charts';
import { useDailyUsage, useSummaryStats, useTopApps, formatTime } from '../hooks/useApi';

const Overview: React.FC = () => {
  const [selectedDate, setSelectedDate] = useState(new Date());
  
  // API calls
  const { data: dailyData, loading: dailyLoading, error: dailyError } = useDailyUsage(selectedDate);
  const { data: summaryData, loading: summaryLoading, error: summaryError } = useSummaryStats(7);
  const { data: topAppsData, loading: topAppsLoading, error: topAppsError } = useTopApps(5, 7);

  const formatDate = (date: Date) => {
    return date.toISOString().split('T')[0];
  };

  if (dailyLoading || summaryLoading || topAppsLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (dailyError || summaryError || topAppsError) {
    return (
      <ErrorMessage 
        message={dailyError || summaryError || topAppsError || 'An error occurred'} 
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Overview</h1>
        <div className="flex items-center space-x-4">
          <label htmlFor="date" className="text-sm font-medium text-gray-700">
            Date:
          </label>
          <input
            type="date"
            id="date"
            value={formatDate(selectedDate)}
            onChange={(e) => setSelectedDate(new Date(e.target.value))}
            className="input"
          />
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Screen Time"
          value={formatTime(dailyData?.total_screen_time || 0)}
          subtitle="Today"
          icon={<Clock className="h-6 w-6" />}
        />
        <StatCard
          title="Active Apps"
          value={dailyData?.top_apps?.length || 0}
          subtitle="Used today"
          icon={<Monitor className="h-6 w-6" />}
        />
        <StatCard
          title="Weekly Average"
          value={formatTime(Math.round(summaryData?.totals?.average_daily_seconds || 0))}
          subtitle="Daily average (7 days)"
          icon={<TrendingUp className="h-6 w-6" />}
        />
        <StatCard
          title="Most Productive"
          value={summaryData?.insights?.most_productive_day?.date ? 
            new Date(summaryData.insights.most_productive_day.date).toLocaleDateString() : 'N/A'}
          subtitle="This week"
          icon={<Calendar className="h-6 w-6" />}
        />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Distribution */}
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Time by Category</h2>
          {dailyData?.categories && dailyData.categories.length > 0 ? (
            <UsageChart
              data={dailyData.categories}
              type="pie"
              height={300}
              dataKey="total_seconds"
              nameKey="category"
            />
          ) : (
            <div className="flex justify-center items-center h-64 text-gray-500">
              No category data for selected date
            </div>
          )}
        </div>

        {/* Top Apps */}
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Top Apps Today</h2>
          {dailyData?.top_apps && dailyData.top_apps.length > 0 ? (
            <div className="space-y-3">
              {dailyData.top_apps.slice(0, 5).map((app, index) => {
                const colors = ['bg-blue-500', 'bg-green-500', 'bg-yellow-500', 'bg-red-500', 'bg-purple-500'];
                return (
                <div key={app.app_name} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className={`w-3 h-3 rounded-full mr-3 ${colors[index % colors.length]}`} />
                    <div>
                      <p className="font-medium text-gray-900">{app.app_name}</p>
                      <p className="text-sm text-gray-500">{app.category}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-gray-900">{formatTime(app.total_seconds)}</p>
                    <p className="text-sm text-gray-500">{app.percentage.toFixed(1)}%</p>
                  </div>
                </div>
                );
              })}
            </div>
          ) : (
            <div className="flex justify-center items-center h-64 text-gray-500">
              No app data for selected date
            </div>
          )}
        </div>
      </div>

      {/* Weekly Top Apps */}
      {topAppsData && topAppsData.apps && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Top Apps This Week</h2>
          <UsageChart
            data={topAppsData.apps}
            type="bar"
            height={300}
            dataKey="total_seconds"
            nameKey="app_name"
          />
        </div>
      )}
    </div>
  );
};

export default Overview;
