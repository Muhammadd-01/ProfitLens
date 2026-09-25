import { createBrowserRouter, Navigate } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { LoginPage } from '@/pages/auth/login';
import { RegisterPage } from '@/pages/auth/register';
import { OverviewPage } from '@/pages/dashboard/overview';
import { ProtectedRoute, PublicOnlyRoute } from '@/components/common/protected-route';

import { DatasetsPage } from '@/pages/datasets/datasets-page';
import { CustomerSegmentsPage } from '@/pages/customers/customer-segments-page';
import { ForecastPage } from '@/pages/forecast/forecast-page';
import { AnomaliesPage } from '@/pages/anomalies/anomalies-page';
import { ProductsPage } from '@/pages/products/products-page';
import { SentimentPage } from '@/pages/sentiment/sentiment-page';
import { InsightsPage } from '@/pages/insights/insights-page';
import { ReportsPage } from '@/pages/reports/reports-page';

// Placeholder pages for routes that will be built in upcoming phases
function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
      <p className="text-muted-foreground">
        This module will be connected as we progress through the analytics phases.
      </p>
    </div>
  );
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/dashboard" replace />,
  },
  {
    element: <PublicOnlyRoute />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: '/dashboard',
        element: <DashboardLayout />,
        children: [
          { index: true, element: <OverviewPage /> },
          { path: 'analytics', element: <PlaceholderPage title="Revenue Analytics" /> },
          { path: 'customers', element: <CustomerSegmentsPage /> },
          { path: 'products', element: <ProductsPage /> },
          { path: 'forecast', element: <ForecastPage /> },
          { path: 'anomalies', element: <AnomaliesPage /> },
          { path: 'sentiment', element: <SentimentPage /> },
          { path: 'insights', element: <InsightsPage /> },
          { path: 'reports', element: <ReportsPage /> },
          { path: 'datasets', element: <DatasetsPage /> },
          { path: 'settings', element: <PlaceholderPage title="Settings" /> },
        ],
      },
    ],
  },
]);
