/**
 * API client for Signal Analyzer backend
 */

import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // Health check
  async health() {
    return this.client.get('/health');
  }

  // Signals
  async getSignals(symbol?: string, limit: number = 10) {
    return this.client.get('/api/signals', {
      params: { symbol, limit },
    });
  }

  async getSignal(id: number) {
    return this.client.get(`/api/signals/${id}`);
  }

  async updateSignal(id: number, data: {
    symbol?: string;
    direction?: 'BUY' | 'SELL';
    order_type?: 'MARKET' | 'LIMIT' | 'STOP';
    entries?: number[];
    stop_loss?: number;
    take_profits?: number[];
    confidence?: number | null;
  }) {
    return this.client.post(`/api/signals/${id}`, data);
  }

  async publishSignal(id: number) {
    return this.client.post(`/api/signals/${id}/publish`, null, { params: { confirm: true } });
  }

  async deleteSignal(id: number, deletePublished: boolean = false) {
    return this.client.delete(`/api/signals/${id}`, { params: { delete_published: deletePublished } });
  }

  async deleteAllSignals(confirm: boolean, deletePublished: boolean = false) {
    return this.client.delete('/api/signals', { params: { confirm, delete_published: deletePublished } });
  }

  // Market data
  async getMarketSnapshot(symbol: string) {
    return this.client.get(`/api/market/${symbol}`);
  }

  // Channels
  async getChannels() {
    return this.client.get('/api/channels');
  }

  async syncChannels() {
    return this.client.post('/api/channels/sync');
  }

  async getChannel(id: number) {
    return this.client.get(`/api/channels/${id}`);
  }

  async updateChannel(
    id: number,
    data: { channel_name?: string; parser_type?: string; enabled?: boolean }
  ) {
    return this.client.post(`/api/channels/${id}`, data);
  }

  // Telegram authentication
  async getTelegramStatus() {
    return this.client.get('/api/telegram/status');
  }

  async telegramConnect(phone: string) {
    return this.client.post('/api/telegram/connect', { phone });
  }

  async telegramVerifyCode(phone: string, code: string) {
    return this.client.post('/api/telegram/verify-code', { phone, code });
  }

  async telegramVerify2FA(password: string) {
    return this.client.post('/api/telegram/verify-2fa', { password });
  }

  async telegramLogout() {
    return this.client.post('/api/telegram/logout');
  }

  // Message types
  async getMessageTypes() {
    return this.client.get('/api/message-types');
  }

  async createMessageType(data: any) {
    return this.client.post('/api/message-types', data);
  }

  async updateMessageType(id: number, data: any) {
    return this.client.put(`/api/message-types/${id}`, data);
  }

  async deleteMessageType(id: number) {
    return this.client.delete(`/api/message-types/${id}`);
  }
}

export const apiClient = new ApiClient();
