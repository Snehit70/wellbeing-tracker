import React, { useState } from 'react';
import { UsageChart, LoadingSpinner, ErrorMessage } from '../components/Charts';
import { useWeeklyUsage, useHourlyUsage, formatTime } from '../hooks/useApi';
import { addDays, format, startOfWeek } from 'date-fns';

const Trends: React.FC = () => {
  const [selectedWeek, setSelectedWeek] = useState(startOfWeek(new Date()));
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [viewType, setViewType] = useState<'weekly' | 'hourly'>('weekly');

  // API calls
  const { data: weeklyData, loading: weeklyLoading, error: weeklyError } = useWeeklyUsage(selectedWeek);
  const { data: hourlyData, loading: hourlyLoading, error: hourlyError } = useHourlyUsage(selectedDate);

  const formatDate = (date: Date) => {
    return date.toISOString().split('T')[0];
  };

  const getDailyChartData = () => {
    if (!weeklyData) return [];
    
    return weeklyData.daily_breakdown.map((day, index) => ({
      day: format(addDays(new Date(weeklyData.start_date), index), 'EEE'),
      date: day.date,
      total_seconds: day.total_screen_time,
      categories: day.categories.reduce((acc: Record<string, number>, cat: any) => {
        acc[cat.category] = cat.total_seconds;
        return acc;
      }, {} as Record<string, number>)
    }));
  };

  const getHourlyChartData = () => {
    if (!hourlyData) return [];
    
    return hourlyData.hourly_data.map(hour => ({
      hour: `${hour.hour}:00`,
      total_seconds: hour.total_seconds,
      apps_count: hour.apps.length
    }));
  };

  if ((viewType === 'weekly' && weeklyLoading) || (viewType === 'hourly' && hourlyLoading)) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if ((viewType === 'weekly' && weeklyError) || (viewType === 'hourly' && hourlyError)) {
    return (
      <ErrorMessage 
        message={weeklyError || hourlyError || 'An error occurred'} 
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Trends</h1>
        <div className="flex items-center space-x-4">
          {/* View Type Toggle */}
          <div className="flex rounded-lg border border-gray-300 overflow-hidden">
            <button
              onClick={() => setViewType('weekly')}
              className={`px-4 py-2 text-sm font-medium ${
                viewType === 'weekly' 
                  ? 'bg-primary-500 text-white' 
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              }`}
            >
              Weekly
            </button>
            <button
              onClick={() => setViewType('hourly')}
              className={`px-4 py-2 text-sm font-medium ${
                viewType === 'hourly' 
                  ? 'bg-primary-500 text-white' 
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              }`}
            >
              Hourly
            </button>
          </div>

          {/* Date Picker */}
          {viewType === 'weekly' ? (
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium text-gray-700">Week of:</label>
              <input
                type="date"
                value={formatDate(selectedWeek)}
                onChange={(e) => setSelectedWeek(startOfWeek(new Date(e.target.value)))}
                className="input"
              />
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium text-gray-700">Date:</label>
              <input
                type="date"
                value={formatDate(selectedDate)}
                onChange={(e) => setSelectedDate(new Date(e.target.value))}
                className="input"
              />
            </div>
          )}
        </div>
      </div>

      {/* Weekly View */}
      {viewType === 'weekly' && weeklyData && (
        <>
          {/* Weekly Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Total Week Time</h3>
              <p className="text-3xl font-bold text-primary-600">
                {formatTime(weeklyData.weekly_totals.reduce((sum, cat) => sum + cat.total_seconds, 0))}
              </p>
            </div>
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Daily Average</h3>
              <p className="text-3xl font-bold text-primary-600">
                {formatTime(Math.round(weeklyData.weekly_totals.reduce((sum, cat) => sum + cat.total_seconds, 0) / 7))}
              </p>
            </div>
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Most Active Day</h3>
              <p className="text-lg font-semibold text-gray-900">
                {weeklyData.daily_breakdown.reduce((max, day) => 
                  day.total_screen_time > max.total_screen_time ? day : max
                ).date}
              </p>
            </div>
          </div>

          {/* Daily Trend Chart */}
          <div className="card">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Daily Screen Time Trend</h2>
            <UsageChart
              data={getDailyChartData()}
              type="line"
              height={400}
              dataKey="total_seconds"
              nameKey="day"
            />
          </div>

          {/* Weekly Category Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Weekly Category Distribution</h2>
              <UsageChart
                data={weeklyData.weekly_totals}
                type="pie"
                height={300}
                dataKey="total_seconds"
                nameKey="category"
              />
            </div>
            
            <div className="card">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Category Trends</h2>
              <UsageChart
                data={weeklyData.weekly_totals}
                type="bar"
                height={300}
                dataKey="total_seconds"
                nameKey="category"
              />
            </div>
          </div>
        </>
      )}

      {/* Hourly View */}
      {viewType === 'hourly' && hourlyData && (
        <>
          {/* Hourly Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Peak Hour</h3>
              <p className="text-2xl font-bold text-primary-600">
                {hourlyData.hourly_data.reduce((max, hour) => 
                  hour.total_seconds > max.total_seconds ? hour : max
                ).hour}:00
              </p>
            </div>
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Active Hours</h3>
              <p className="text-2xl font-bold text-primary-600">
                {hourlyData.hourly_data.filter(hour => hour.total_seconds > 0).length}
              </p>
            </div>
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Peak Usage</h3>
              <p className="text-2xl font-bold text-primary-600">
                {formatTime(Math.max(...hourlyData.hourly_data.map(h => h.total_seconds)))}
              </p>
            </div>
          </div>

          {/* Hourly Activity Chart */}
          <div className="card">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Hourly Activity - {format(selectedDate, 'MMMM d, yyyy')}
            </h2>
            <UsageChart
              data={getHourlyChartData()}
              type="bar"
              height={400}
              dataKey="total_seconds"
              nameKey="hour"
            />
          </div>

          {/* Hourly Breakdown Table */}
          <div className="card">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Detailed Hourly Breakdown</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Hour
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Total Time
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Apps Used
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Top App
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {hourlyData.hourly_data.filter(hour => hour.total_seconds > 0).map((hour) => (
                    <tr key={hour.hour}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {hour.hour}:00 - {hour.hour}:59
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatTime(hour.total_seconds)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {hour.apps.length}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {hour.apps.length > 0 ? 
                          `${hour.apps[0].app_name} (${formatTime(hour.apps[0].total_seconds)})` : 
                          'No activity'
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Trends;
