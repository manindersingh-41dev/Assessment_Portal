/** Authenticated application shell. */

import React, { useCallback, useState } from 'react';
import { Outlet } from 'react-router-dom';
import Header from '../components/Header.jsx';
import Sidebar from '../components/Sidebar.jsx';

export const AppLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const closeSidebar = useCallback(() => setSidebarOpen(false), []);
  const toggleSidebar = useCallback(() => setSidebarOpen((open) => !open), []);

  return (
    <div className="min-h-dvh min-w-0 bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <Sidebar isOpen={sidebarOpen} onClose={closeSidebar} />
      <div className="min-h-dvh min-w-0 md:pl-64">
        <a
          href="#main-content"
          className="sr-only z-50 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-primary-700 shadow focus:not-sr-only focus:fixed focus:left-4 focus:top-4 dark:bg-slate-900 dark:text-primary-300"
        >
          Skip to content
        </a>
        <Header onMenuClick={toggleSidebar} />
        <main id="main-content" tabIndex={-1} className="mx-auto w-full max-w-screen-2xl px-4 py-5 outline-none sm:px-6 sm:py-7 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
