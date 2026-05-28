import { positions, account, alerts, wsConnected } from '$lib/stores';
import type { Position, AccountInfo, Alert } from '$lib/types';

let socket: WebSocket | null = null;
let pingInterval: ReturnType<typeof setInterval> | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectAttempts = 0;
let intentionalClose = false;

const PING_INTERVAL_MS = 25_000;
const MAX_BACKOFF_MS = 30_000;

type ServerMessage =
	| { type: 'positions_update'; data: { positions: Position[] } }
	| { type: 'account_update'; data: AccountInfo }
	| { type: 'alert'; data: Alert }
	| { type: 'pong'; data: Record<string, never> };

function backoffDelay(attempt: number): number {
	return Math.min(1000 * 2 ** attempt, MAX_BACKOFF_MS);
}

function wsUrl(token: string): string {
	const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
	return `${proto}://${window.location.host}/ws?token=${encodeURIComponent(token)}`;
}

function handleMessage(raw: string) {
	let msg: ServerMessage;
	try {
		msg = JSON.parse(raw);
	} catch {
		return;
	}
	switch (msg.type) {
		case 'positions_update':
			positions.set(msg.data.positions);
			break;
		case 'account_update':
			account.set(msg.data);
			break;
		case 'alert':
			alerts.update((current) => [msg.data, ...current]);
			break;
		case 'pong':
			break;
	}
}

function clearPing() {
	if (pingInterval !== null) {
		clearInterval(pingInterval);
		pingInterval = null;
	}
}

function clearReconnect() {
	if (reconnectTimer !== null) {
		clearTimeout(reconnectTimer);
		reconnectTimer = null;
	}
}

function scheduleReconnect() {
	if (intentionalClose) return;
	clearReconnect();
	const delay = backoffDelay(reconnectAttempts);
	reconnectAttempts += 1;
	reconnectTimer = setTimeout(() => {
		const token = localStorage.getItem('futra_token');
		if (token) open(token);
	}, delay);
}

function open(token: string) {
	if (socket && socket.readyState !== WebSocket.CLOSED) return;
	intentionalClose = false;

	const ws = new WebSocket(wsUrl(token));
	socket = ws;

	ws.onopen = () => {
		reconnectAttempts = 0;
		wsConnected.set(true);
		clearPing();
		pingInterval = setInterval(() => {
			if (ws.readyState === WebSocket.OPEN) {
				ws.send(JSON.stringify({ type: 'ping' }));
			}
		}, PING_INTERVAL_MS);
	};

	ws.onmessage = (event) => handleMessage(event.data);

	ws.onerror = () => {
		// Let onclose handle the reconnect — onerror always fires before close.
	};

	ws.onclose = () => {
		wsConnected.set(false);
		clearPing();
		socket = null;
		scheduleReconnect();
	};
}

export function connectWebSocket(): void {
	if (typeof window === 'undefined') return;
	const token = localStorage.getItem('futra_token');
	if (!token) return;
	open(token);
}

export function disconnectWebSocket(): void {
	intentionalClose = true;
	clearReconnect();
	clearPing();
	if (socket) {
		try {
			socket.close(1000, 'client disconnect');
		} catch {
			/* ignore */
		}
		socket = null;
	}
	wsConnected.set(false);
	reconnectAttempts = 0;
}
