import React from 'react';
import { Laptop } from 'lucide-react';

const isUnsupportedMobileOS = () => {
  if (typeof navigator === 'undefined') return false;

  const userAgent = navigator.userAgent || '';
  const platform = navigator.userAgentData?.platform || navigator.platform || '';
  const isAndroid = /android/i.test(`${userAgent} ${platform}`);
  const isIOS = /iPhone|iPad|iPod/i.test(userAgent)
    || (/Macintosh|MacIntel/i.test(`${userAgent} ${platform}`) && navigator.maxTouchPoints > 1);

  return isAndroid || isIOS;
};

export const isMobileOSBlocked = isUnsupportedMobileOS();

const MobileOSBlocked = () => (
  <main className="flex min-h-dvh items-center justify-center bg-slate-950 px-6 py-12 text-slate-100">
    <section className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-8 text-center shadow-2xl">
      <Laptop className="mx-auto mb-5 h-10 w-10 text-primary-400" aria-hidden="true" />
      <h1 className="text-2xl font-bold">Use a desktop or laptop</h1>
      <p className="mt-3 text-sm leading-6 text-slate-300">
        The assessment portal is unavailable on Android and iOS devices. Please open it on a desktop or laptop computer.
      </p>
    </section>
  </main>
);

export default MobileOSBlocked;
