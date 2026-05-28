<script lang="ts">
	import { positions } from '$lib/stores';
	import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '$lib/components/ui/table/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import CircleOff from '@lucide/svelte/icons/circle-off';

	function formatCurrency(value: number): string {
		return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
	}

	function formatSignedCurrency(value: number): string {
		const sign = value >= 0 ? '+' : '';
		return sign + formatCurrency(value);
	}

	let loading = $state(false);
</script>

{#if $positions.length === 0}
	{#if !loading}
		<div class="flex flex-col items-center justify-center py-16 text-center">
			<CircleOff class="h-12 w-12 text-muted-foreground mb-4" />
			<h2 class="text-lg font-semibold">No Active Positions</h2>
			<p class="text-sm text-muted-foreground mt-2 max-w-[320px]">Trading has not started yet. Positions will appear here once the EA opens trades.</p>
		</div>
	{:else}
		<div class="space-y-2">
			{#each Array(5) as _}
				<Skeleton class="h-10 w-full rounded-md" />
			{/each}
		</div>
	{/if}
{:else}
	<div class="overflow-x-auto">
		<Table>
			<TableHeader>
				<TableRow>
					<TableHead>Ticket</TableHead>
					<TableHead>Symbol</TableHead>
					<TableHead class="text-center">Direction</TableHead>
					<TableHead class="text-right">Volume</TableHead>
					<TableHead class="text-right">Open Price</TableHead>
					<TableHead class="text-right">Current Price</TableHead>
					<TableHead class="text-right">P&amp;L</TableHead>
					<TableHead class="text-right">SL</TableHead>
					<TableHead class="text-right">TP</TableHead>
				</TableRow>
			</TableHeader>
			<TableBody>
				{#each $positions as pos}
					<TableRow>
						<TableCell class="px-4 py-2">{pos.ticket}</TableCell>
						<TableCell class="px-4 py-2">{pos.symbol}</TableCell>
						<TableCell class="px-4 py-2 text-center">
							{#if pos.direction === 'buy'}
								<Badge variant="default" class="bg-green-400/10 text-green-400 border-green-400/20">Buy</Badge>
							{:else}
								<Badge variant="destructive" class="bg-red-400/10 text-red-400 border-red-400/20">Sell</Badge>
							{/if}
						</TableCell>
						<TableCell class="px-4 py-2 text-right">{pos.volume.toFixed(2)}</TableCell>
						<TableCell class="px-4 py-2 text-right font-tabular">{pos.open_price.toFixed(5)}</TableCell>
						<TableCell class="px-4 py-2 text-right font-tabular">{pos.current_price.toFixed(5)}</TableCell>
						<TableCell class="px-4 py-2 text-right font-tabular">
							<span class={pos.profit >= 0 ? 'text-green-400' : 'text-red-400'}>
								{formatSignedCurrency(pos.profit)}
							</span>
						</TableCell>
						<TableCell class="px-4 py-2 text-right font-tabular">{pos.sl.toFixed(5)}</TableCell>
						<TableCell class="px-4 py-2 text-right font-tabular">{pos.tp.toFixed(5)}</TableCell>
					</TableRow>
				{/each}
			</TableBody>
		</Table>
	</div>
{/if}
