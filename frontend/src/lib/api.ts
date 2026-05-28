import type { Position, AccountInfo, Trade, Decision, EquityPoint, DrawdownPoint, Alert, StrategyConfig } from '$lib/types';

const BASE = '';

function getToken(): string | null {
	if (typeof localStorage === 'undefined') return null;
	return localStorage.getItem('futra_token');
}

async function fetchApi<T>(path: string, options: RequestInit = {}): Promise<T> {
	const token = getToken();
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...(options.headers as Record<string, string> || {}),
	};
	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}
	const res = await fetch(`${BASE}${path}`, { ...options, headers });
	if (res.status === 401) {
		localStorage.removeItem('futra_token');
		if (typeof window !== 'undefined') window.location.href = '/login';
		throw new Error('Unauthorized');
	}
	if (!res.ok) {
		throw new Error(`API error: ${res.status} ${res.statusText}`);
	}
	return res.json();
}

// Auth
export async function login(username: string, password: string): Promise<{ token: string; expires_at: string }> {
	const res = await fetch(`${BASE}/api/auth/login`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ username, password }),
	});
	if (!res.ok) throw new Error('Invalid credentials');
	const data = await res.json();
	localStorage.setItem('futra_token', data.token);
	return data;
}

export async function logout(): Promise<void> {
	await fetchApi('/api/auth/logout', { method: 'POST' });
	localStorage.removeItem('futra_token');
	if (typeof window !== 'undefined') window.location.href = '/login';
}

// Data endpoints
export const getPositions = () => fetchApi<Position[]>('/api/positions');
export const getAccount = () => fetchApi<AccountInfo>('/api/account');
export const getTrades = (limit = 50, offset = 0) => fetchApi<Trade[]>(`/api/trades?limit=${limit}&offset=${offset}`);
export const getDecisions = (limit = 50, offset = 0, symbol?: string) => {
	let url = `/api/decisions?limit=${limit}&offset=${offset}`;
	if (symbol) url += `&symbol=${symbol}`;
	return fetchApi<Decision[]>(url);
};
export const getEquityCurve = (days = 30) => fetchApi<EquityPoint[]>(`/api/equity-curve?days=${days}`);
export const getDrawdown = (days = 30) => fetchApi<DrawdownPoint[]>(`/api/drawdown?days=${days}`);
export const getAlerts = (acknowledged?: boolean) => {
	let url = '/api/alerts';
	if (acknowledged !== undefined) url += `?acknowledged=${acknowledged}`;
	return fetchApi<Alert[]>(url);
};
export const acknowledgeAlert = (id: number) => fetchApi<void>(`/api/alerts/${id}/acknowledge`, { method: 'POST' });
export const getStrategy = () => fetchApi<StrategyConfig>('/api/strategy');
