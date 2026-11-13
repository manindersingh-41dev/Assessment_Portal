import React, { useEffect } from 'react';
import { Outlet } from 'react-router-dom';

const StudentPortalProtection = () => {
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
    return () => {
      document.removeEventListener('contextmenu', preventContextMenu, true);
      document.removeEventListener('keydown', blockDeveloperToolsShortcuts, true);
    };
  }, []);

  return <Outlet />;
};

export default StudentPortalProtection;
