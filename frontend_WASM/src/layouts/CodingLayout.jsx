import React from 'react';
import { Outlet } from 'react-router-dom';

const CodingLayout = () => {
  return (
    <div className="min-h-dvh min-w-0 bg-slate-950 text-slate-100 lg:h-dvh lg:min-h-0 lg:overflow-hidden">
      <main className="min-w-0 lg:h-full lg:min-h-0">
        <Outlet />
      </main>
    </div>
  );
};

export default CodingLayout;
