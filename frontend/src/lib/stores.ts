import { writable } from 'svelte/store';
import type { Position, AccountInfo, Trade, Decision, Alert } from '$lib/types';

export const positions = writable<Position[]>([]);
export const account = writable<AccountInfo | null>(null);
export const trades = writable<Trade[]>([]);
export const decisions = writable<Decision[]>([]);
export const alerts = writable<Alert[]>([]);
export const wsConnected = writable<boolean>(false);
export const isAuthenticated = writable<boolean>(false);
export const userName = writable<string>('');
