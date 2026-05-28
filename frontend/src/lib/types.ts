export interface Position {
	ticket: number;
	symbol: string;
	direction: 'buy' | 'sell';
	volume: number;
	open_price: number;
	current_price: number;
	sl: number;
	tp: number;
	profit: number;
	swap: number;
	open_time: string;
}

export interface AccountInfo {
	balance: number;
	equity: number;
	margin: number;
	free_margin: number;
	daily_pnl: number;
}

export interface Trade {
	ticket: number;
	symbol: string;
	direction: string;
	entry_price: number;
	exit_price: number;
	profit: number;
	open_time: string;
	close_time: string;
	duration: string;
	regime: string | null;
}

export interface Decision {
	timestamp: string;
	symbol: string;
	timeframe: string;
	regime: 'trending' | 'ranging' | 'volatile' | 'quiet';
	confidence: number;
	sl_pips: number;
	tp_pips: number;
	lot_size: number;
	reasoning: string;
}

export interface EquityPoint {
	time: string;
	value: number;
}

export interface DrawdownPoint {
	time: string;
	value: number;
}

export interface Alert {
	id: number;
	type: string;
	message: string;
	severity: 'info' | 'warning' | 'critical';
	acknowledged: boolean;
	created_at: string;
}

export interface StrategyConfig {
	config: Record<string, unknown>;
}
