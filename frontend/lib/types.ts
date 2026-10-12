/**
 * Types and interfaces for the application
 */

export interface Signal {
  id: number;
  message_id: number;
  symbol: string;
  direction: 'BUY' | 'SELL';
  order_type: 'LIMIT' | 'MARKET';
  entries: number[];
  stop_loss: number;
  take_profits: number[];
  confidence?: number;
  status: string;
  raw_signal_type?: string;
  normalized_json: string;
  created_at: string;
  updated_at: string;
  channel_id: number;
  channel_name?: string | null;
  category: 'crypto' | 'cfds';
  message_type_id?: number;
}

export interface MarketSymbol {
  name: string;
  description: string | null;
  type: string | null;
  exchange: string | null;
  source: string | null;
  digits: number | null;
  is_active: boolean | null;
  has_data: boolean | null;
}

export interface EconomicCalendarEvent {
  id: string | null;
  event_id: string | null;
  time: string;
  period: string | null;
  country_code: string | null;
  currency: string | null;
  name: string | null;
  importance: string | null;
  event_type: string | null;
  unit: string | null;
  digits: number | null;
  actual: number | null;
  forecast: number | null;
  previous: number | null;
  revised_previous: number | null;
  time_mode: string | null;
  source_url: string | null;
  source: string | null;
}

export interface EconomicCalendarResponse {
  provider: string;
  source: string;
  requested_from: string;
  requested_to: string;
  fetched_at: string;
  events: EconomicCalendarEvent[];
}

export interface Channel {
  id: number;
  platform: string;
  external_channel_id: string;
  channel_name: string;
  category: 'crypto' | 'cfds';
  username?: string;
  channel_type?: string;
  enabled: boolean;
  parser_type?: string;
  created_at: string;
  updated_at: string;
}

export interface AvailableChannel {
  external_channel_id: string;
  channel_name: string;
  username?: string;
  channel_type: string;
  already_added: boolean;
}

export interface TelegramStatus {
  connected: boolean;
  listening: boolean;
  enabled_count: number;
  password_required: boolean;
  phone?: string;
  username?: string;
  user_id?: number;
}

export interface SignalMessageType {
  id: number;
  name: string;
  description?: string;
  parser_name: string;
  enabled: boolean;
  configuration_json?: string;
  created_at: string;
  updated_at: string;
}

export interface TradeSetup {
  id: number;
  signal_id: number;
  analysis_id?: number;
  analysis_run_id?: number;
  status: string;
  direction: string;
  preferred_entry?: number;
  entry_zone_low?: number;
  entry_zone_high?: number;
  stop_loss: number;
  risk_reward?: number;
  entries: { price: number; allocation_percent: number; sequence: number }[];
  targets: { price: number; sequence: number }[];
  created_at: string;
  updated_at: string;
}

export interface SignalEvent {
  id: number;
  signal_id: number;
  event_type: string;
  price?: number;
  notes?: string;
  created_at: string;
}

export interface RMultiple {
  label: string;
  price: number;
  risk: number;
  reward: number;
  r_multiple: number;
}

export interface RiskReward {
  entry: number;
  stop_loss: number;
  risk: number;
  targets: RMultiple[];
}

export interface ZoneTouchEvent {
  started_at: string;
  ended_at: string;
  candle_count: number;
  extreme_price: number;
  reaction_type?: string;
}

export interface SRZone {
  id: number;
  symbol: string;
  timeframe: string;
  zone_type: 'support' | 'resistance';
  lower_price: number;
  upper_price: number;
  center_price: number;
  touch_count: number;
  first_touch_at?: string;
  last_touch_at?: string;
  strength: number;
  is_psychological: boolean;
  touch_events: ZoneTouchEvent[];
}

export interface MarketOverview {
  symbol: string;
  price?: number;
  timestamp?: string;
  market_open: boolean;
}

export interface MarketQuote {
  provider: string;
  symbol: string;
  price_basis: string;
  price: number | null;
  bid: number | null;
  ask: number | null;
  source: string | null;
  timestamp: string | null;
  fetched_at: string | null;
  quote_age_seconds: number | null;
  market_state: string;
  status: 'live' | 'stale' | 'closed' | 'unknown' | 'unavailable';
  day_change_percent: number | null;
  error: string | null;
}

export interface DashboardResponse {
  market_overview: MarketOverview;
  latest_signals: Signal[];
  active_signals: Signal[];
  sr_zones: SRZone[];
  generated_at: string;
}

export interface ZoneSummary {
  zone_type: string;
  lower: number;
  upper: number;
  center: number;
  touch_count: number;
  strength: number;
  distance?: number;
  last_touch_at?: string;
}

export interface ProximitySummary {
  event_type: string;
  zone_type: string;
  zone_lower: number;
  zone_upper: number;
  distance: number;
  touch_count: number;
  strength: number;
}

export interface SignalAnalysis {
  signal_id?: number;
  analysis_run_id: number;
  market_timestamp?: string;
  model_version?: string;
  regime: string;
  structure?: string;
  current_price?: number;
  nearest_support?: ZoneSummary;
  nearest_resistance?: ZoneSummary;
  liquidity?: any;
  fvg?: any;
  signal_proximity?: ProximitySummary;
  structure_summary?: any;
  liquidity_summary?: any;
  supply_demand_summary?: any;
  fvg_summary?: any;
  indicator_summary?: any;
  timeframes?: Record<string, any>;
  decision: string;
  reasoning: string;
  created_at: string;
}

export interface ChannelStats {
  channel_id: number;
  messages_today: number;
  signals_today: number;
  active_signals: number;
  successes: number;
  failures: number;
}
