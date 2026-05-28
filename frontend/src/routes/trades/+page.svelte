<script lang="ts">
	import { onMount } from 'svelte';
	import { getTrades } from '$lib/api';
	import TradeHistoryTable from '$lib/components/TradeHistoryTable.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import type { Trade } from '$lib/types';

	let trades = $state<Trade[]>([]);
	let loading = $state(true);
	let error = $state('');
	let offset = $state(0);
	const pageSize = 50;

	async function fetchTrades(newOffset = 0) {
		loading = true;
		error = '';
		try {
			const data = await getTrades(pageSize, newOffset);
			trades = data;
			offset = newOffset;
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	function exportCSV() {
		const headers = ['Ticket', 'Symbol', 'Direction', 'Entry Price', 'Exit Price', 'Profit', 'Duration', 'Date'];
		const rows = trades.map(t => [
			t.ticket,
			t.symbol,
			t.direction,
			t.entry_price.toFixed(5),
			t.exit_price.toFixed(5),
			t.profit.toFixed(2),
			t.duration,
			t.close_time
		]);
		const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
		const blob = new Blob([csv], { type: 'text/csv' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = 'trades.csv';
		a.click();
		URL.revokeObjectURL(url);
	}

	onMount(() => {
		fetchTrades();
	});
</script>

<div class="space-y-6">
	<div class="flex items-center justify-between">
		<h1 class="text-xl font-semibold">Trade History</h1>
		<Button variant="outline" onclick={exportCSV} disabled={trades.length === 0}>
			Export CSV
		</Button>
	</div>

	{#if error}
		<div class="flex flex-col items-center justify-center py-12 text-center">
			<h2 class="text-lg font-semibold">Unable to Load Data</h2>
			<p class="text-sm text-muted-foreground mt-2">{error}</p>
			<Button class="mt-4" variant="outline" onclick={() => fetchTrades()}>Retry</Button>
		</div>
	{:else}
		<TradeHistoryTable {trades} {loading} />

		<div class="flex justify-center gap-2 mt-4">
			<Button variant="outline" size="sm" disabled={offset === 0 || loading} onclick={() => fetchTrades(offset - pageSize)}>
				Previous
			</Button>
			<Button variant="outline" size="sm" disabled={trades.length < pageSize || loading} onclick={() => fetchTrades(offset + pageSize)}>
				Next
			</Button>
		</div>
	{/if}
</div>
