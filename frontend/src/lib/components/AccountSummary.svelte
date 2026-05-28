<script lang="ts">
	import { account } from '$lib/stores';
	import MetricsCard from './MetricsCard.svelte';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';

	function formatCurrency(value: number | undefined): string {
		if (value === undefined || value === null) return '\u2014';
		return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
	}
</script>

{#if $account === null}
	<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
		{#each Array(4) as _}
			<Skeleton class="h-[120px] w-full rounded-md" />
		{/each}
	</div>
{:else}
	<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
		<MetricsCard
			label="Balance"
			value={formatCurrency($account?.balance)}
			tooltip="Total account balance including closed trade profits."
		/>
		<MetricsCard
			label="Equity"
			value={formatCurrency($account?.equity)}
			tooltip="Balance + floating P&L from open positions."
		/>
		<MetricsCard
			label="Margin"
			value={formatCurrency($account?.margin)}
			tooltip="Funds reserved to maintain open positions."
		/>
		<MetricsCard
			label="Free Margin"
			value={formatCurrency($account?.free_margin)}
			tooltip="Equity \u2212 Margin. Available for new positions."
		/>
	</div>
{/if}
