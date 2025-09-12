import { useState, useEffect } from 'react';
import { format } from 'date-fns';

const API_BASE_URL = 'http://localhost:8847';

// Custom hook for API calls
export function useApi<T>(endpoint: string, dependencies: any[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refetchTrigger, setRefetchTrigger] = useState(0);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch(`${API_BASE_URL}${endpoint}`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
        setData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [...dependencies, refetchTrigger]);

  const refetch = () => {
    setRefetchTrigger(prev => prev + 1);
  };

  return { data, loading, error, refetch };
}

// Hook for daily usage data
export function useDailyUsage(date: Date) {
  const formattedDate = format(date, 'yyyy-MM-dd');
  return useApi<{
    date: string;
    total_screen_time: number;
    categories: Array<{ app_name: string; category: string; total_seconds: number; percentage: number }>;
    top_apps: Array<{ app_name: string; category: string; total_seconds: number; percentage: number }>;
  }>(`/usage/daily?date=${formattedDate}`, [formattedDate]);
}

// Hook for weekly usage data  
export function useWeeklyUsage(startDate: Date) {
  const formattedDate = format(startDate, 'yyyy-MM-dd');
  return useApi<{
    start_date: string;
    end_date: string;
    daily_breakdown: any[];
    weekly_totals: Array<{ app_name: string; category: string; total_seconds: number; percentage: number }>;
  }>(`/usage/weekly?start=${formattedDate}`, [formattedDate]);
}

// Hook for top apps
export function useTopApps(limit = 10, days = 7) {
  return useApi<{
    apps: Array<{ app_name: string; category: string; total_seconds: number; percentage: number }>;
    total_apps: number;
  }>(`/apps/top?limit=${limit}&days=${days}`, [limit, days]);
}

// Hook for hourly breakdown
export function useHourlyUsage(date: Date) {
  const formattedDate = format(date, 'yyyy-MM-dd');
  return useApi<{
    date: string;
    hourly_data: Array<{ hour: number; total_seconds: number; apps: any[] }>;
  }>(`/usage/hourly?date=${formattedDate}`, [formattedDate]);
}

// Hook for categories
export function useCategories() {
  return useApi<{
    categories: Record<string, { name: string; apps: string[]; color: string; description: string }>;
  }>('/categories', []);
}

// Hook for summary stats
export function useSummaryStats(days = 30) {
  return useApi<{
    period: { start_date: string; end_date: string; days: number };
    totals: { screen_time_seconds: number; screen_time_hours: number; average_daily_seconds: number; average_daily_hours: number };
    insights: { unique_apps_used: number; most_productive_day: { date: string | null; work_seconds: number } };
    fallback?: boolean;
  }>(`/stats/summary?days=${days}`, [days]);
}

// Utility functions
export function formatTime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else if (minutes > 0) {
    return `${minutes}m`;
  } else {
    return `${seconds}s`;
  }
}

export function formatTimeDetailed(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  const parts: string[] = [];
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);
  
  return parts.join(' ');
}

export async function updateAppCategory(appName: string, categoryName: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/categories/${categoryName}/apps`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      app_name: appName,
      category: categoryName,
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to update app category');
  }
}

export async function removeAppFromCategory(appName: string, categoryName: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/categories/${categoryName}/apps/${appName}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error('Failed to remove app from category');
  }
}
