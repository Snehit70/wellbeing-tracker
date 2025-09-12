// API Response Types
export interface UsageData {
  app_name: string;
  category: string;
  total_seconds: number;
  percentage: number;
}

export interface DailyUsageResponse {
  date: string;
  total_screen_time: number;
  categories: UsageData[];
  top_apps: UsageData[];
}

export interface WeeklyUsageResponse {
  start_date: string;
  end_date: string;
  daily_breakdown: DailyUsageResponse[];
  weekly_totals: UsageData[];
}

export interface TopAppsResponse {
  apps: UsageData[];
  total_apps: number;
}

export interface HourlyUsageData {
  hour: number;
  total_seconds: number;
  apps: UsageData[];
}

export interface HourlyBreakdownResponse {
  date: string;
  hourly_data: HourlyUsageData[];
}

export interface CategoryInfo {
  name: string;
  apps: string[];
  color: string;
  description: string;
}

export interface CategoriesResponse {
  categories: Record<string, CategoryInfo>;
}

export interface SummaryStats {
  period: {
    start_date: string;
    end_date: string;
    days: number;
  };
  totals: {
    screen_time_seconds: number;
    screen_time_hours: number;
    average_daily_seconds: number;
    average_daily_hours: number;
  };
  insights: {
    unique_apps_used: number;
    most_productive_day: {
      date: string | null;
      work_seconds: number;
    };
  };
}

// Component Props Types
export interface DateRangePickerProps {
  startDate: Date;
  endDate: Date;
  onDateChange: (start: Date, end: Date) => void;
}

export interface UsageChartProps {
  data: UsageData[];
  type: 'pie' | 'bar' | 'line';
  height?: number;
}

export interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
}

// Utility Types
export type TimeFormat = 'hours' | 'minutes' | 'seconds';
export type ViewPeriod = 'day' | 'week' | 'month';
export type ChartType = 'pie' | 'bar' | 'line' | 'area';
