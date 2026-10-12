import React, { useEffect, useState } from 'react';
import { CalendarCheck, CalendarDays, RefreshCw } from 'lucide-react';
import { Layout } from '@/components/Layout';
import { apiClient } from '@/lib/api';
import { EconomicCalendarEvent } from '@/lib/types';

type Importance = 'all' | 'low' | 'medium' | 'high';
type EventType = 'all' | 'event' | 'indicator' | 'holiday';

function localDateInput(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}
function eventTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(value));
}

function displayEventTime(event: EconomicCalendarEvent): string {
  switch (event.time_mode?.toLowerCase()) {
    case 'date': return '—';
    case 'tentative': return '~';
    default: return eventTime(event.time);
  }
}

function eventDay(value: string): string {
  return new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'short', day: 'numeric' }).format(new Date(value));
}

function formatValue(value: number | null, event: EconomicCalendarEvent): string {
  if (value === null || !Number.isFinite(value)) return '—';
  const digits = Math.max(0, Math.min(event.digits ?? 3, 8));
  const formatted = new Intl.NumberFormat(undefined, { maximumFractionDigits: digits }).format(value);
  const unit = event.unit?.toLowerCase();
  if (unit === 'currency') return event.currency ? `${formatted} ${event.currency}` : formatted;
  if (unit === 'percent' || unit === 'percentage') return `${formatted}%`;
  return event.unit ? `${formatted} ${event.unit}` : formatted;
}

function actualValueStyle(event: EconomicCalendarEvent): string {
  const previous = event.revised_previous ?? event.previous;
  if (event.actual === null || previous === null) return 'text-slate-300';
  if (event.actual > previous) return 'text-emerald-300';
  if (event.actual < previous) return 'text-red-300';
  return 'text-slate-300';
}

function actualComparison(event: EconomicCalendarEvent): string {
  const previous = event.revised_previous ?? event.previous;
  if (event.actual === null) return 'Actual not released';
  if (previous === null) return 'Previous value unavailable';
  if (event.actual > previous) return 'Above previous';
  if (event.actual < previous) return 'Below previous';
  return 'Equal to previous';
}

function importanceStyle(importance: string | null): string {
  switch (importance?.toLowerCase()) {
    case 'high': return 'bg-red-400';
    case 'medium': return 'bg-amber-300';
    case 'low': return 'bg-slate-500';
    default: return 'bg-slate-600';
  }
}

export default function EconomicCalendarPage() {
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [countries, setCountries] = useState('');
  const [importance, setImportance] = useState<Importance>('medium');
  const [eventType, setEventType] = useState<EventType>('all');
  const [events, setEvents] = useState<EconomicCalendarEvent[]>([]);
  const [fetchedAt, setFetchedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [localTimeZone, setLocalTimeZone] = useState('');

  useEffect(() => {
    setLocalTimeZone(Intl.DateTimeFormat().resolvedOptions().timeZone);
    const today = new Date();
    const end = new Date(today);
    end.setDate(end.getDate() + 7);
    setFromDate(localDateInput(today));
    setToDate(localDateInput(end));
  }, []);

  useEffect(() => {
    if (!fromDate || !toDate) return;
    const from = new Date(`${fromDate}T00:00:00`).toISOString();
    const to = new Date(`${toDate}T23:59:59.999`).toISOString();
    let active = true;
    setLoading(true);
    setError(null);
    apiClient.getEconomicCalendar({
      from,
      to,
      countries: countries.trim().replace(/\s+/g, '').toUpperCase() || undefined,
      importance: importance === 'all' ? undefined : importance,
      type: eventType === 'all' ? undefined : eventType,
      limit: 200,
    }).then(({ data }) => {
      if (!active) return;
      setEvents(data.events);
      setFetchedAt(data.fetched_at);
    }).catch((requestError: unknown) => {
      if (!active) return;
      setError('Calendar data is unavailable or the selected range is invalid. Check the filters and try again.');
      console.error(requestError);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [fromDate, toDate, countries, importance, eventType, refreshVersion]);

  const grouped = new Map<string, EconomicCalendarEvent[]>();
  for (const event of events) {
    const day = eventDay(event.time);
    grouped.set(day, [...(grouped.get(day) ?? []), event]);
  }
  const maxToDate = fromDate ? (() => {
    const latest = new Date(`${fromDate}T00:00:00`);
    latest.setDate(latest.getDate() + 30);
    return localDateInput(latest);
  })() : undefined;

  return (
    <Layout title="Economic Calendar - Signal Analyzer">
      <div className="space-y-6">
        <header className="flex flex-wrap items-end justify-between gap-4 border-b border-[var(--glass-border)] pb-5">
          <div>
            <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--glass-border)] bg-white/5 text-[var(--glass-accent)]">
              <CalendarDays size={20} aria-hidden="true" />
            </div>
            <h2 className="text-2xl font-bold text-white">Economic Calendar</h2>
            <p className="mt-1 text-sm text-slate-400">Scheduled releases and revisions · times shown in {localTimeZone || 'your local timezone'}</p>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="rounded border border-emerald-300/20 bg-emerald-400/10 px-2 py-1 text-emerald-200">Biquote</span>
            {fetchedAt && <span>Updated {new Date(fetchedAt).toLocaleTimeString()}</span>}
          </div>
        </header>

        <section aria-label="Calendar filters" className="flex flex-wrap items-end gap-3">
          <label className="grid gap-1 text-xs text-slate-400">From
            <input className="glass-input !w-auto" type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} />
          </label>
          <label className="grid gap-1 text-xs text-slate-400">To
            <input className="glass-input !w-auto" type="date" value={toDate} min={fromDate || undefined} max={maxToDate} onChange={(event) => setToDate(event.target.value)} />
          </label>
          <button type="button" onClick={() => { const today = localDateInput(new Date()); setFromDate(today); setToDate(today); }} className="glass-icon-button flex h-10 items-center gap-2 px-3 text-sm" aria-label="Show today's events">
            <CalendarCheck size={15} aria-hidden="true" />Today
          </button>
          <label className="grid gap-1 text-xs text-slate-400">Countries
            <input className="glass-input w-40 uppercase" type="text" value={countries} onChange={(event) => setCountries(event.target.value)} placeholder="US, EU, TR" aria-label="Filter by country codes" />
          </label>
          <label className="grid gap-1 text-xs text-slate-400">Impact
            <select className="glass-input !w-auto" value={importance} onChange={(event) => setImportance(event.target.value as Importance)}>
              <option value="all">All</option><option value="medium">Medium and above</option><option value="high">High</option><option value="low">Low and above</option>
            </select>
          </label>
          <label className="grid gap-1 text-xs text-slate-400">Type
            <select className="glass-input !w-auto" value={eventType} onChange={(event) => setEventType(event.target.value as EventType)}>
              <option value="all">All types</option><option value="event">Events</option><option value="indicator">Indicators</option><option value="holiday">Holidays</option>
            </select>
          </label>
          <button type="button" onClick={() => setRefreshVersion((version) => version + 1)} disabled={loading || !fromDate || !toDate} className="glass-icon-button flex h-10 items-center gap-2 px-3 text-sm disabled:opacity-50" aria-label="Refresh calendar">
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} aria-hidden="true" />Refresh
          </button>
        </section>

        {error && <p role="alert" className="border-y border-red-300/20 py-3 text-sm text-red-200">{error}</p>}
        <section aria-label="Economic releases" aria-busy={loading} className="theme-band overflow-hidden border-y">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--glass-border)] bg-white/[0.025] px-4 py-3 text-xs uppercase text-slate-400">
            <span>Economic releases</span>
            <span className="flex items-center gap-3 normal-case"><span className="text-emerald-300">Above previous</span><span className="text-red-300">Below previous</span></span>
            <span>{importance === 'all' ? 'All impact levels' : `${importance} impact and above`}</span>
          </div>
          {loading && events.length === 0 ? (
            <p role="status" className="px-4 py-12 text-center text-sm text-slate-400">Loading calendar…</p>
          ) : !error && events.length === 0 ? (
            <p className="px-4 py-12 text-center text-sm text-slate-400">No releases found for these filters.</p>
          ) : (
            <div className="max-w-full overflow-x-auto">
              <table className="w-full min-w-[720px] border-collapse text-left text-sm">
                <thead className="theme-table-head text-[11px] uppercase text-slate-400">
                  <tr><th scope="col" className="px-4 py-3 font-medium">Time <span className="ml-1 normal-case text-slate-500">{localTimeZone ? `(${localTimeZone})` : '(local)'}</span></th><th scope="col" className="px-3 py-3 font-medium">Country</th><th scope="col" className="px-3 py-3 font-medium">Event</th><th scope="col" className="px-3 py-3 text-right font-medium">Actual <span className="normal-case text-slate-500">vs previous</span></th><th scope="col" className="px-3 py-3 text-right font-medium">Forecast</th><th scope="col" className="px-4 py-3 text-right font-medium">Previous</th></tr>
                </thead>
                <tbody>
                  {[...grouped.entries()].map(([day, dayEvents]) => (
                    <React.Fragment key={day}>
                      <tr className="border-y border-[var(--glass-border)] bg-white/[0.035]"><th colSpan={6} className="px-4 py-2 text-xs font-semibold text-slate-300">{day}</th></tr>
                      {dayEvents.map((event, index) => (
                        <tr key={event.event_id || event.id || `${event.time}-${event.country_code}-${index}`} className="theme-table-row border-b border-[var(--glass-border)] align-middle">
                          <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-300">{displayEventTime(event)}</td>
                          <td className="px-3 py-3 font-mono text-xs text-slate-400">{event.country_code || '—'}</td>
                          <td className="max-w-[420px] px-3 py-3">
                            <div className="flex min-w-0 items-center gap-2">
                              <span className={`h-2 w-2 shrink-0 rounded-full ${importanceStyle(event.importance)}`} title={`${event.importance || 'Unknown'} impact`} />
                              {event.source_url ? <a className="truncate font-medium text-slate-100 hover:text-[var(--glass-accent)]" href={event.source_url} target="_blank" rel="noreferrer">{event.name || 'Untitled release'}</a> : <span className="truncate font-medium text-slate-100">{event.name || 'Untitled release'}</span>}
                            </div>
                          </td>
                          <td className={`whitespace-nowrap px-3 py-3 text-right font-mono ${actualValueStyle(event)}`} title={actualComparison(event)}>{formatValue(event.actual, event)}</td>
                          <td className="whitespace-nowrap px-3 py-3 text-right font-mono text-slate-300">{formatValue(event.forecast, event)}</td>
                          <td className="whitespace-nowrap px-4 py-3 text-right font-mono text-slate-300">
                            {formatValue(event.revised_previous ?? event.previous, event)}
                            {event.revised_previous !== null && <span className="ml-1 text-[10px] text-amber-200">revised</span>}
                          </td>
                        </tr>
                      ))}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <footer className="flex flex-wrap justify-between gap-2 border-t border-[var(--glass-border)] px-4 py-3 text-xs text-slate-400">
            <span>{events.length} releases · local time</span><span>Source: Biquote economic calendar</span>
          </footer>
        </section>
      </div>
    </Layout>
  );
}