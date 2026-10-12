import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Check, Loader2, LogOut, Pencil, Radio, RefreshCw, Search, Send } from 'lucide-react';
import { Layout } from '@/components/Layout';
import { apiClient } from '@/lib/api';
import { Channel, TelegramStatus } from '@/lib/types';

function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error) && typeof error.response?.data?.detail === 'string') {
    return error.response.data.detail;
  }
  return 'Unable to complete the request. Please try again.';
}

export default function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [status, setStatus] = useState<TelegramStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const [search, setSearch] = useState('');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [step, setStep] = useState<'phone' | 'code' | 'password'>('phone');
  const [channelToEnable, setChannelToEnable] = useState<Channel | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<'crypto' | 'cfds'>('cfds');
  const [categoryOnly, setCategoryOnly] = useState(false);

  async function load(sync: boolean) {
    const connection = await apiClient.getTelegramStatus();
    setStatus(connection.data);
    if (connection.data.password_required) setStep('password');
    const response = sync && connection.data.connected
      ? await apiClient.syncChannels()
      : await apiClient.getChannels();
    setChannels(response.data.filter((channel: Channel) => channel.platform === 'telegram'));
    if (connection.data.connected) setStatus((await apiClient.getTelegramStatus()).data);
  }

  useEffect(() => {
    load(true).catch((failure) => setError(errorMessage(failure))).finally(() => setLoading(false));
    const interval = setInterval(() => {
      apiClient.getTelegramStatus().then((response) => setStatus(response.data)).catch(() => {});
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  async function refresh() {
    setBusy(true);
    setError(null);
    try {
      await load(true);
      setNotice('Channels refreshed');
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setBusy(false);
    }
  }

  async function authenticate(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const response = step === 'phone'
        ? await apiClient.telegramConnect(phone.trim())
        : step === 'code'
          ? await apiClient.telegramVerifyCode(phone.trim(), code.trim())
          : await apiClient.telegramVerify2FA(password);
      setCode('');
      setPassword('');
      if (response.data.connected) {
        await load(true);
        setStep('phone');
        setNotice('Telegram connected');
      } else {
        setStep(response.data.password_required ? 'password' : 'code');
      }
    } catch (failure) {
      setCode('');
      setPassword('');
      setError(errorMessage(failure));
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    if (!window.confirm('Log out of Telegram on this device?')) return;
    setBusy(true);
    setError(null);
    try {
      await apiClient.telegramLogout();
      setStep('phone');
      setPhone('');
      setCode('');
      setPassword('');
      await load(false);
      setNotice('Telegram logged out');
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setBusy(false);
    }
  }

  async function saveChannelSelection(channel: Channel, enabled: boolean, category?: 'crypto' | 'cfds'): Promise<boolean> {
    setSaving((current) => [...current, channel.id]);
    setError(null);
    setNotice('');
    try {
      const response = await apiClient.updateChannel(channel.id, { enabled, ...(category ? { category } : {}) });
      setChannels((current) => current.map((item) => item.id === channel.id ? response.data : item));
      setStatus((await apiClient.getTelegramStatus()).data);
      setNotice(`${channel.channel_name}: ${response.data.enabled ? `selected for ${response.data.category === 'crypto' ? 'Crypto' : 'CFDs'}` : 'deselected'}`);
      return true;
    } catch (failure) {
      setError(errorMessage(failure));
      return false;
    } finally {
      setSaving((current) => current.filter((id) => id !== channel.id));
    }
  }

  function toggle(channel: Channel) {
    if (channel.enabled) {
      void saveChannelSelection(channel, false);
      return;
    }
    setCategoryOnly(false);
    setSelectedCategory(channel.category || 'cfds');
    setChannelToEnable(channel);
  }

  async function confirmChannelSelection() {
    if (!channelToEnable) return;
    const channel = channelToEnable;
    const saved = categoryOnly
      ? await saveChannelCategory(channel, selectedCategory)
      : await saveChannelSelection(channel, true, selectedCategory);
    if (saved) {
      setChannelToEnable(null);
    }
  }

  async function saveChannelCategory(channel: Channel, category: 'crypto' | 'cfds'): Promise<boolean> {
    setSaving((current) => [...current, channel.id]);
    setError(null);
    setNotice('');
    try {
      const response = await apiClient.updateChannel(channel.id, { category });
      setChannels((current) => current.map((item) => item.id === channel.id ? response.data : item));
      setNotice(`${channel.channel_name}: category changed to ${category === 'crypto' ? 'Crypto' : 'CFDs'}`);
      return true;
    } catch (failure) {
      setError(errorMessage(failure));
      return false;
    } finally {
      setSaving((current) => current.filter((id) => id !== channel.id));
    }
  }

  const selected = channels.filter((channel) => channel.enabled).length;
  const filtered = channels.filter((channel) =>
    `${channel.channel_name} ${channel.external_channel_id}`.toLowerCase().includes(search.toLowerCase())
  ).sort((first, second) =>
    Number(second.enabled) - Number(first.enabled) || first.channel_name.localeCompare(second.channel_name)
  );
  const inputClass = 'glass-input';

  return (
    <Layout title="Channels - Signal Analyzer">
      <div className="space-y-6 text-slate-200">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <h2 className="text-2xl font-semibold text-white">Telegram Channels</h2>
          <div className="flex items-center gap-2 text-sm">
            <Radio size={16} className={status?.connected ? 'text-emerald-400' : 'text-amber-400'} />
            {status?.connected ? 'Connected' : 'Not connected'}
            {status?.connected && <button type="button" onClick={logout} title="Log out of Telegram" aria-label="Log out of Telegram" disabled={busy || saving.length > 0} className="glass-icon-button ml-2 flex h-9 w-9 items-center justify-center disabled:opacity-40"><LogOut size={16} /></button>}
          </div>
        </div>

        {error && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 border-l-2 border-red-400 bg-red-950/30 px-4 py-3 text-sm text-red-200"><span>{error}</span><button type="button" disabled={busy || saving.length > 0} onClick={refresh} className="flex items-center gap-2 disabled:opacity-40"><RefreshCw size={14} />Retry</button></div>}
        <div aria-live="polite" className="min-h-5 text-sm text-emerald-400">{notice}</div>

        {!loading && status && !status.connected && (
          <form onSubmit={authenticate} className="glass-surface max-w-md space-y-4 p-5">
            <h3 className="font-semibold text-white">Connect Telegram</h3>
            <div>
              <label htmlFor="telegram-phone" className="mb-2 block text-sm">Phone number</label>
              <input id="telegram-phone" type="tel" autoComplete="tel" placeholder="+1234567890" required pattern="\+[1-9][0-9]{6,14}" value={phone} disabled={step !== 'phone' || busy} onChange={(event) => setPhone(event.target.value)} className={inputClass} />
            </div>
            {step === 'code' && <div>
              <label htmlFor="telegram-code" className="mb-2 block text-sm">Telegram login code</label>
              <input id="telegram-code" inputMode="numeric" autoComplete="one-time-code" required value={code} onChange={(event) => setCode(event.target.value)} className={inputClass} />
            </div>}
            {step === 'password' && <div>
              <label htmlFor="telegram-password" className="mb-2 block text-sm">Two-step verification password</label>
              <input id="telegram-password" type="password" autoComplete="off" required value={password} onChange={(event) => setPassword(event.target.value)} className={inputClass} />
            </div>}
            <div className="flex gap-4">
              <button type="submit" disabled={busy} className="glass-primary-button flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
                {busy ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                {step === 'phone' ? 'Send Code' : 'Verify'}
              </button>
              {step !== 'phone' && <button type="button" disabled={busy} onClick={() => { setStep('phone'); setCode(''); setPassword(''); }} className="text-sm text-slate-400">Start Again</button>}
            </div>
          </form>
        )}

        <section aria-label="Channel selection">
          <div className="flex flex-wrap items-center justify-between gap-4 py-4">
            <div className="text-sm"><span className="font-semibold text-white">{selected}</span> selected <span className="ml-3 text-slate-400">{status?.listening && selected > 0 ? 'Listening' : 'Paused'}</span></div>
            <div className="flex w-full items-center gap-3 sm:w-auto">
              <div className="relative min-w-0 flex-1">
                <Search size={16} className="absolute left-3 top-3.5 text-slate-500" />
                <input aria-label="Search channels" placeholder="Search channels" value={search} onChange={(event) => setSearch(event.target.value)} className={`${inputClass} !pl-9 text-sm`} />
              </div>
              <button type="button" title="Refresh Telegram channels" aria-label="Refresh Telegram channels" onClick={refresh} disabled={busy || loading || !status?.connected || saving.length > 0} className="glass-icon-button flex h-11 w-11 shrink-0 items-center justify-center disabled:opacity-40">
                <RefreshCw size={18} className={busy ? 'animate-spin' : ''} />
              </button>
            </div>
          </div>
          {loading ? <div role="status" className="flex items-center gap-2 py-8 text-sm text-slate-400"><Loader2 size={18} className="animate-spin" />Loading channels</div>
            : filtered.length === 0 ? <div className="py-8 text-sm text-slate-400">{search ? 'No matching channels' : 'No channels available'}</div>
              : <ul className="space-y-2">
                {filtered.map((channel) => <li key={channel.id} className="glass-surface channel-row" data-selected={channel.enabled}>
                  <div className="flex min-h-20 items-center gap-3 px-4 py-4 sm:gap-4">
                    <label className="flex shrink-0 cursor-pointer items-center gap-3" aria-label={`Listen to ${channel.channel_name}`}>
                      <input type="checkbox" checked={channel.enabled} disabled={saving.includes(channel.id) || busy} onChange={() => toggle(channel)} aria-label={`Listen to ${channel.channel_name}`} className="h-5 w-5 shrink-0 accent-sky-400" />
                      <span className="hidden h-10 w-10 items-center justify-center rounded-lg bg-blue-400/15 text-sky-300 sm:flex"><Radio size={19} aria-hidden="true" /></span>
                    </label>
                    <div className="min-w-0 flex-1"><div className="break-words font-medium text-white">{channel.channel_name}</div><div className="mt-1 break-all text-xs text-slate-500">{channel.external_channel_id}</div><span className="mt-2 inline-flex rounded border border-[var(--glass-border)] bg-white/5 px-2 py-0.5 text-xs text-slate-300">{channel.category === 'crypto' ? 'Crypto' : 'CFDs'}</span></div>
                    <button type="button" disabled={busy || saving.includes(channel.id)} onClick={() => { setCategoryOnly(true); setSelectedCategory(channel.category); setChannelToEnable(channel); }} className="glass-icon-button flex h-9 shrink-0 items-center gap-2 px-2 text-xs disabled:opacity-40 sm:px-3"><Pencil size={14} /><span className="hidden sm:inline">Change type</span></button>
                    <span className="flex shrink-0 items-center gap-2 text-xs text-slate-400">
                      {saving.includes(channel.id) ? <Loader2 size={16} className="animate-spin" /> : channel.enabled ? <Check size={16} className="text-emerald-400" /> : null}
                      {saving.includes(channel.id) ? 'Saving' : channel.enabled ? (status?.listening ? 'Listening' : 'Selected') : 'Off'}
                    </span>
                  </div>
                </li>)}
              </ul>}
        </section>
      </div>
      {channelToEnable && <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setChannelToEnable(null); }}>
        <section role="dialog" aria-modal="true" aria-labelledby="channel-category-title" className="theme-dialog w-full max-w-md space-y-5 rounded-lg border p-5 shadow-2xl">
          <div><h3 id="channel-category-title" className="text-lg font-semibold text-white">{categoryOnly ? 'Change channel type' : 'Categorize channel'}</h3><p className="mt-1 break-words text-sm text-slate-400">{channelToEnable.channel_name}</p></div>
          <fieldset className="space-y-2"><legend className="mb-2 text-sm text-slate-300">Listen to this channel under</legend>{(['crypto', 'cfds'] as const).map((categoryOption) => <label key={categoryOption} className={`flex cursor-pointer items-center gap-3 rounded-md border p-3 ${selectedCategory === categoryOption ? 'border-[var(--glass-accent)] bg-[var(--glass-hover)]' : 'border-[var(--glass-border)]'}`}><input type="radio" name="channel-category" value={categoryOption} checked={selectedCategory === categoryOption} onChange={() => setSelectedCategory(categoryOption)} className="accent-[var(--glass-accent)]" /><span className="text-sm text-white">{categoryOption === 'crypto' ? 'Crypto' : 'CFDs'}</span></label>)}</fieldset>
          <div className="flex justify-end gap-3 border-t border-[var(--glass-border)] pt-4"><button type="button" onClick={() => setChannelToEnable(null)} className="glass-icon-button px-4 py-2 text-sm">Cancel</button><button type="button" onClick={confirmChannelSelection} disabled={saving.includes(channelToEnable.id)} className="glass-primary-button rounded-md px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{saving.includes(channelToEnable.id) ? 'Saving' : categoryOnly ? 'Save type' : 'Save and Listen'}</button></div>
        </section>
      </div>}
    </Layout>
  );
}