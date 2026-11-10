/** Dashboard header with page context, theme control, and account menu. */

import React, { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ChevronDown, GraduationCap, LogOut, Menu, Moon, Sun, UserRound } from 'lucide-react';
import { useAuthStore } from '../store/authStore.js';
import { useThemeStore } from '../store/themeStore.js';
import { Badge } from './Common.jsx';

const getPageTitle = (pathname) => {
  const routes = [
    ['/faculty/dashboard', 'Faculty dashboard'],
    ['/faculty/questions/create', 'Create question'],
    ['/faculty/questions', 'Question bank'],
    ['/faculty/assessments/create', 'Create assessment'],
    ['/faculty/assessments', 'Assessments'],
    ['/faculty/results', 'Results'],
    ['/faculty/profile', 'Profile'],
    ['/student/dashboard', 'Student dashboard'],
    ['/student/assessments/active', 'Active assessments'],
    ['/student/assessments/upcoming', 'Upcoming assessments'],
    ['/student/assessments/completed', 'Completed assessments'],
    ['/student/assessments', 'My assessments'],
    ['/student/submissions', 'My submissions'],
    ['/student/results', 'My results'],
    ['/student/profile', 'Profile'],
    ['/assessment/', 'Assessment workspace'],
  ];
  return routes.find(([path]) => pathname === path || pathname.startsWith(path + '/') || path.endsWith('/') && pathname.startsWith(path))?.[1] || 'Assessment portal';
};

const getInitials = (user) => {
  const first = user?.first_name?.trim()?.[0] || user?.email?.trim()?.[0] || 'U';
  const last = user?.last_name?.trim()?.[0] || '';
  return `${first}${last}`.toUpperCase();
};

export const Header = ({ onMenuClick }) => {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const theme = useThemeStore((state) => state.theme);
  const toggleTheme = useThemeStore((state) => state.toggleTheme);
  const [menuPath, setMenuPath] = useState(null);
  const menuRootRef = useRef(null);
  const menuRef = useRef(null);
  const triggerRef = useRef(null);
  const menuId = 'account-menu';
  const pageTitle = getPageTitle(pathname);
  const menuOpen = menuPath === pathname;
  const displayName = user?.full_name || [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.email || 'Account';
  const profilePath = user?.role === 'faculty' ? '/faculty/profile' : '/student/profile';

  useEffect(() => {
    if (!menuOpen) return undefined;

    const onPointerDown = (event) => {
      if (!menuRootRef.current?.contains(event.target)) {
        setMenuPath(null);
      }
    };
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        setMenuPath(null);
        triggerRef.current?.focus();
      } else if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
        const items = [...(menuRef.current?.querySelectorAll('[role="menuitem"]') || [])];
        if (!items.length) return;
        event.preventDefault();
        if (event.key === 'Home') items[0].focus();
        else if (event.key === 'End') items.at(-1).focus();
        else if (event.key === 'ArrowDown') {
          const current = items.indexOf(document.activeElement);
          items[(current + 1) % items.length].focus();
        } else {
          const current = items.indexOf(document.activeElement);
          items[(current <= 0 ? items.length : current) - 1].focus();
        }
      }
    };

    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [menuOpen]);

  const handleLogout = () => {
    setMenuPath(null);
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white/95 px-3 backdrop-blur dark:border-slate-800 dark:bg-slate-900/95 sm:px-5 lg:px-7">
      <div className="flex min-w-0 items-center gap-3">
        {onMenuClick && (
          <button
            type="button"
            onClick={onMenuClick}
            className="rounded-lg p-2 text-slate-600 transition hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-slate-300 dark:hover:bg-slate-800 md:hidden"
            aria-label="Open navigation menu"
            aria-controls="primary-navigation"
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
          </button>
        )}
        <Link to={user?.role === 'faculty' ? '/faculty/dashboard' : '/student/dashboard'} className="flex min-w-0 items-center gap-2.5 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 md:hidden">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary-600 text-white">
            <GraduationCap className="h-5 w-5" aria-hidden="true" />
          </span>
          <span className="truncate text-sm font-bold text-slate-900 dark:text-white">Geeta Assessment</span>
        </Link>
        <div className="hidden min-w-0 md:block">
          <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">{pageTitle}</p>
          <p className="text-xs capitalize text-slate-500 dark:text-slate-400">{user?.role || 'Workspace'}</p>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-1.5 sm:gap-3">
        <button
          type="button"
          onClick={toggleTheme}
          className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white"
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? <Sun className="h-5 w-5" aria-hidden="true" /> : <Moon className="h-5 w-5" aria-hidden="true" />}
        </button>

        <div className="relative" ref={menuRootRef}>
          <button
            ref={triggerRef}
            type="button"
            onClick={() => setMenuPath(menuOpen ? null : pathname)}
            className="flex items-center gap-2 rounded-xl p-1.5 pr-2 text-left transition hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:hover:bg-slate-800 sm:pr-3"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            aria-controls={menuId}
            aria-label={`Account menu for ${displayName}`}
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-xs font-bold text-primary-700 dark:bg-primary-900/70 dark:text-primary-200" aria-hidden="true">
              {getInitials(user)}
            </span>
            <span className="hidden max-w-40 sm:block">
              <span className="block truncate text-sm font-semibold text-slate-800 dark:text-slate-100">{displayName}</span>
              <span className="block text-left text-[11px] capitalize text-slate-500 dark:text-slate-400">{user?.role || 'Account'}</span>
            </span>
            <ChevronDown className={`hidden h-4 w-4 text-slate-400 transition sm:block ${menuOpen ? 'rotate-180' : ''}`} aria-hidden="true" />
          </button>

          {menuOpen && (
            <div id={menuId} ref={menuRef} role="menu" aria-label="Account actions" className="absolute right-0 mt-2 w-64 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl ring-1 ring-black/5 dark:border-slate-700 dark:bg-slate-900">
              <div className="border-b border-slate-100 px-4 py-3 dark:border-slate-800">
                <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">{displayName}</p>
                <p className="mt-0.5 truncate text-xs text-slate-500 dark:text-slate-400">{user?.email}</p>
                {user?.role && <Badge className="mt-2" variant={user.role === 'faculty' ? 'primary' : 'info'}>{user.role}</Badge>}
              </div>
              <div className="p-1.5">
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setMenuPath(null);
                    navigate(profilePath);
                  }}
                  className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-slate-700 transition hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  <UserRound className="h-4 w-4" aria-hidden="true" /> Profile
                </button>
                <button
                  type="button"
                  role="menuitem"
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-rose-700 transition hover:bg-rose-50 focus:outline-none focus:ring-2 focus:ring-rose-500 dark:text-rose-300 dark:hover:bg-rose-950/40"
                >
                  <LogOut className="h-4 w-4" aria-hidden="true" /> Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
