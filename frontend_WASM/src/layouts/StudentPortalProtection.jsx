import React, { useEffect, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { isChildrenDay } from '../utils/isChildrenDay.js';

const StudentPortalProtection = () => {
  const location = useLocation();
  const [childrenDay, setChildrenDay] = useState(() => isChildrenDay());

  useEffect(() => {
    const preventContextMenu = (event) => event.preventDefault();
    const blockDeveloperToolsShortcuts = (event) => {
      const key = event.key.toLowerCase();
      const modifier = event.ctrlKey || event.metaKey;
      const inspectShortcut = modifier && event.shiftKey && ['i', 'j', 'c', 'k'].includes(key);
      const macInspectShortcut = event.metaKey && event.altKey && ['i', 'j', 'c'].includes(key);
      const blocked = key === 'f12'
        || (modifier && key === 'u')
        || inspectShortcut
        || macInspectShortcut;

      if (blocked) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    };

    document.addEventListener('contextmenu', preventContextMenu, true);
    document.addEventListener('keydown', blockDeveloperToolsShortcuts, true);
    const dayCheck = window.setInterval(() => setChildrenDay(isChildrenDay()), 30_000);
    return () => {
      document.removeEventListener('contextmenu', preventContextMenu, true);
      document.removeEventListener('keydown', blockDeveloperToolsShortcuts, true);
      window.clearInterval(dayCheck);
    };
  }, []);

  if (childrenDay && location.pathname.startsWith('/assessment/')) {
    return <Navigate to="/childrens-day" replace />;
  }

  return <Outlet />;
};

export default StudentPortalProtection;
