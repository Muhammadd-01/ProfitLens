import { Outlet } from 'react-router-dom';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Sidebar } from './sidebar';
import { TopBar } from './topbar';

export function DashboardLayout() {
  return (
    <TooltipProvider delay={0}>
      <div className="flex min-h-screen bg-background">
        <Sidebar />
        {/* Main area shifts right to account for sidebar (w-60 = 15rem, collapsed w-16 = 4rem) */}
        <div className="ml-60 flex flex-1 flex-col transition-all duration-300">
          <TopBar />
          <main className="flex-1 overflow-auto p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}
