<script lang="ts">
	import type { Trade } from '$lib/types';
	import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '$lib/components/ui/table/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import Receipt from '@lucide/svelte/icons/receipt';

	let {
		trades = [],
		loading = false
	}: {
		trades: Trade[];
		loading: boolean;
	} = $props();

	function formatCurrency(value: number): string {
		return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
	}

	function formatSignedCurrency(value: number): string {
		const sign = value >= 0 ? '+' : '';
		return sign + formatCurrency(value);
	}

	function formatDate(iso: string): string {
		const d = new Date(iso);
		return d.toISOString().replace('T', ' ').substring(0, 19);
	}
</script>

{#if loading}
	<div class="space-y-2">
		{#each Array(8) as _}
			<Skeleton class="h-10 w-full rounded-md" />
		{/each}
	</div>
{:else if trades.length === 0}
	<div class="flex flex-col items-center justify-center py-16 text-center">
		<Receipt class="h-12 w-12 text-muted-foreground mb-4" />
		<h2 class="text-lg font-semibold">No Trade History</h2>
		<p class="text-sm text-muted-foreground mt-2 max-w-[320px]">Completed trades will appear here with entry/exit prices, profit, and duration.</p>
	</div>
{:else}
	<div class="overflow-x-auto">
		<Table>
			<TableHeader>
				<TableRow>
					<TableHead>Ticket</TableHead>
					<TableHead>Symbol</TableHead>
					<TableHead class="text-center">Direction</TableHead>
					<TableHead class="text-right">Entry Price</TableHead>
					<TableHead class="text-right">Exit Price</TableHead>
					<TableHead class="text-right">Profit</TableHead>
					<TableHead>Duration</TableHead>
					<TableHead>Date</TableHead>
				</TableRow>
			</TableHeader>
			<TableBody>
				{#each trades as trade}
					<TableRow>
						<TableCell class="px-4 py-2">{trade.ticket}</TableCell>
						<TableCell class="px-4 py-2">{trade.symbol}</TableCell>
						<TableCell class="px-4 py-2 text-center">
							{#if trade.direction === 'buy'}
								<Badge variant="default" class="bg-green-400/10 text-green-400 border-green-400/20">Buy</Badge>
							{:else}
								<Badge variant="destructive" class="bg-red-400/10 text-red-400 border-red-400/20">Sell</Badge>
							{/if}
						</TableCell>
						<TableCell class="px-4 py-2 text-right font-tabular">{trade.entry_price.toFixed(5)}</TableCell>
						<TableCell class="px-4 py-2 text-right font-tabular">{trade.exit_price.toFixed(5)}</TableCell>
						<TableCell class="px-4 py-2 text-right font-tabular">
							<span class={trade.profit > 0 ? 'text-green-400' : trade.profit < 0 ? 'text-red-400' : 'text-gray-400'}>
								{formatSignedCurrency(trade.profit)}
							</span>
						</TableCell>
						<TableCell class="px-4 py-2">{trade.duration}</TableCell>
						<TableCell class="px-4 py-2">{formatDate(trade.close_time)}</TableCell>
					</TableRow>
				{/each}
			</TableBody>
		</Table>
	</div>
{/if}
