/** Responsive, role-specific primary navigation. */

import React, { useEffect, useRef, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  BarChart3,
  BookOpen,
  CalendarClock,
  ClipboardCheck,
  Code2,
  GraduationCap,
  LayoutDashboard,
  UserRound,
  X,
} from 'lucide-react';
import { useAuthStore } from '../store/authStore.js';

const studentNavigation = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/student/dashboard' },
  { label: 'My assessments', icon: ClipboardCheck, path: '/student/assessments' },
  { label: 'Active assessments', icon: Code2, path: '/student/assessments/active' },
  { label: 'Upcoming assessments', icon: CalendarClock, path: '/student/assessments/upcoming' },
  { label: 'Completed assessments', icon: BookOpen, path: '/student/assessments/completed' },
  { label: 'My submissions', icon: Code2, path: '/student/submissions' },
  { label: 'My results', icon: BarChart3, path: '/student/results' },
  { label: 'Profile', icon: UserRound, path: '/student/profile' },
];

const facultyNavigation = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/faculty/dashboard' },
  { label: 'Question bank', icon: BookOpen, path: '/faculty/questions' },
  { label: 'Assessments', icon: ClipboardCheck, path: '/faculty/assessments' },
  { label: 'Results', icon: BarChart3, path: '/faculty/results' },
  { label: 'Profile', icon: UserRound, path: '/faculty/profile' },
];

const getInitials = (user) => {
  const first = user?.first_name?.trim()?.[0] || user?.email?.trim()?.[0] || 'U';
  const last = user?.last_name?.trim()?.[0] || '';
  return `${first}${last}`.toUpperCase();
};

export const Sidebar = ({ isOpen = false, onClose = () => {} }) => {
  const user = useAuthStore((state) => state.user);
  const { pathname } = useLocation();
  const [isDesktop, setIsDesktop] = useState(false);
  const sidebarRef = useRef(null);
  const closeButtonRef = useRef(null);
  const isFaculty = user?.role === 'faculty';
  const navigation = isFaculty ? facultyNavigation : studentNavigation;
  const workspaceLabel = isFaculty ? 'Faculty workspace' : 'Student workspace';
  const displayName = user?.full_name || [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.email || 'Account';

  useEffect(() => {
    const media = window.matchMedia('(min-width: 768px)');
    const update = () => setIsDesktop(media.matches);
    update();
    media.addEventListener?.('change', update);
    return () => media.removeEventListener?.('change', update);
  }, []);

  useEffect(() => {
    onClose();
  }, [pathname, onClose]);

  useEffect(() => {
    if (!isOpen || isDesktop) return undefined;

    const previousFocus = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    closeButtonRef.current?.focus();
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        onClose();
        return;
      }
      if (event.key !== 'Tab' || !sidebarRef.current) return;

      const focusable = [...sidebarRef.current.querySelectorAll(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', onKeyDown);
      if (previousFocus instanceof HTMLElement) previousFocus.focus();
    };
  }, [isOpen, isDesktop, onClose]);

  return (
    <>
      {!isDesktop && isOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 cursor-default bg-slate-950/45 backdrop-blur-[1px] md:hidden"
          onClick={onClose}
          aria-label="Close navigation menu"
        />
      )}
      <aside
        ref={sidebarRef}
        id="primary-navigation"
        aria-label={`${isFaculty ? 'Faculty' : 'Student'} navigation`}
        aria-hidden={!isDesktop && !isOpen}
        aria-modal={!isDesktop && isOpen ? true : undefined}
        role={!isDesktop && isOpen ? 'dialog' : undefined}
        inert={!isDesktop && !isOpen ? true : undefined}
        className={`fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] flex-col border-r border-slate-200 bg-white shadow-xl transition-transform duration-200 ease-out dark:border-slate-800 dark:bg-slate-900 md:z-40 md:w-64 md:max-w-none md:translate-x-0 md:shadow-none ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}
      >
        <div className="flex h-16 shrink-0 items-center justify-between border-b border-slate-100 px-5 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-600 text-white shadow-sm">
              <GraduationCap className="h-5 w-5" aria-hidden="true" />
            </span>
            <div>
              <p className="text-sm font-bold tracking-tight text-slate-900 dark:text-white">Geeta University</p>
              <p className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Assessment portal</p>
            </div>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-slate-300 dark:hover:bg-slate-800 md:hidden"
            aria-label="Close navigation menu"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div className="shrink-0 px-5 pb-2 pt-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400 dark:text-slate-500">{workspaceLabel}</p>
        </div>
        <nav className="min-h-0 flex-1 space-y-1 overflow-y-auto px-3 pb-5" aria-label="Workspace pages">
          {navigation.map(({ label, icon: Icon, path }) => (
            <NavLink
              key={path}
              to={path}
              end
              onClick={onClose}
              className={({ isActive }) => `group flex min-h-10 items-center gap-3 rounded-lg px-3.5 py-2 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 ${isActive ? 'bg-primary-50 font-semibold text-primary-700 dark:bg-primary-950/60 dark:text-primary-300' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white'}`}
            >
              {({ isActive }) => (
                <>
                  <Icon className={`h-[18px] w-[18px] shrink-0 ${isActive ? 'text-primary-600 dark:text-primary-300' : 'text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-200'}`} aria-hidden="true" />
                  <span>{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="shrink-0 border-t border-slate-100 p-4 dark:border-slate-800">
          <div className="flex min-w-0 items-center gap-3 rounded-xl bg-slate-50 px-3 py-2.5 dark:bg-slate-800/70">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-xs font-bold text-primary-700 shadow-sm dark:bg-slate-700 dark:text-primary-200" aria-hidden="true">
              {getInitials(user)}
            </span>
            <div className="min-w-0">
              <p className="truncate text-xs font-semibold text-slate-800 dark:text-slate-100">{displayName}</p>
              <p className="truncate text-[11px] capitalize text-slate-500 dark:text-slate-400">{user?.role || 'Account'}</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
