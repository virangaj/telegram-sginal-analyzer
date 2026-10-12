/**
 * Dashboard layout
 */

import React from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { Activity, CalendarDays, Radio } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
  title?: string;
}

export const Layout: React.FC<LayoutProps> = ({
  children,
  title = 'Signal Analyzer',
}) => {
  const { pathname, query } = useRouter();
  const activeCategory = query.category === 'crypto' ? 'crypto' : 'cfds';
  return (
    <>
      <Head>
        <title>{title}</title>
        <meta name="description" content="Trading signal analysis platform" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <div className="theme-shell min-h-screen">
        <header className="theme-header">
          <div className="max-w-screen-2xl mx-auto px-4 py-4 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="brand-icon text-white"><Activity size={23} aria-hidden="true" /></span>
              <h1 className="text-xl font-bold text-white">Signal Analyzer</h1>
            </div>
            <nav aria-label="Main navigation" className="flex flex-wrap justify-end gap-2 text-sm">
              <Link href={{ pathname: '/', query: { category: 'crypto' } }} aria-current={pathname === '/' && activeCategory === 'crypto' ? 'page' : undefined} className="theme-nav">Crypto</Link>
              <Link href={{ pathname: '/', query: { category: 'cfds' } }} aria-current={pathname === '/' && activeCategory === 'cfds' ? 'page' : undefined} className="theme-nav">CFDs</Link>
              <Link href="/calendar" aria-current={pathname === '/calendar' ? 'page' : undefined} className="theme-nav"><CalendarDays size={17} aria-hidden="true" />Economic Calendar</Link>
              <Link href="/channels" aria-current={pathname === '/channels' ? 'page' : undefined} className="theme-nav"><Radio size={17} aria-hidden="true" />Channels</Link>
            </nav>
          </div>
        </header>
        <main className="max-w-screen-2xl mx-auto px-4 py-8">
          {children}
        </main>
      </div>
    </>
  );
};
