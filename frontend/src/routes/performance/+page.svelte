<script lang="ts">
	import { onMount } from 'svelte';
	import { getEquityCurve, getDrawdown } from '$lib/api';
	import EquityChart from '$lib/components/EquityChart.svelte';
	import DrawdownChart from '$lib/components/DrawdownChart.svelte';
	import MetricsCard from '$lib/components/MetricsCard.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import LineChart from '@lucide/svelte/icons/line-chart';
	import type { EquityPoint, DrawdownPoint } from '$lib/types';

	let equityData = $state<EquityPoint[]>([]);
	let drawdownData = $state<DrawdownPoint[]>([]);
	let loading = $state(true);
	let error = $state('');
	let days = $state(30);
	let activeRange = $state('30D');

	const ranges = [
		{ label: '7D', value: 7 },
		{ label: '30D', value: 30 },
		{ label: '90D', value: 90 },
		{ label: 'All', value: 365 },
	];

	async function fetchData(selectedDays: number) {
		loading = true;
		error = '';
		days = selectedDays;
		try {
			const [equity, drawdown] = await Promise.all([
				getEquityCurve(selectedDays),
				getDrawdown(selectedDays),
			]);
			equityData = equity;
			drawdownData = drawdown;
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		fetchData(30);
	});
</script>

<div class="space-y-6">
	<h1 class="text-xl font-semibold">Performance</h1>

	<!-- Time range selector -->
	<div class="flex gap-2">
		{#each ranges as range}
			<Button
				variant={activeRange === range.label ? 'default' : 'outline'}
				size="sm"
				onclick={() => { activeRange = range.label; fetchData(range.value); }}
				disabled={loading}
			>
				{range.label}
			</Button>
		{/each}
	</div>

	<!-- Metrics row -->
	<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
		<MetricsCard label="Sharpe Ratio" value="\u2014" tooltip="Risk-adjusted return. Higher = better. > 1.0 is good." />
		<MetricsCard label="Sortino Ratio" value="\u2014" tooltip="Like Sharpe but only penalizes downside volatility." />
		<MetricsCard label="Max Drawdown" value="\u2014" tooltip="Largest peak-to-trough decline as percentage." />
		<MetricsCard label="Profit Factor" value="\u2014" tooltip="Gross profit / Gross loss. > 1.0 means profitable." />
	</div>

	{#if loading}
		<div class="flex items-center justify-center h-[400px]">
			<Spinner class="h-8 w-8" />
		</div>
	{:else if error}
		<div class="flex flex-col items-center justify-center py-12 text-center">
			<h2 class="text-lg font-semibold">Unable to Load Data</h2>
			<p class="text-sm text-muted-foreground mt-2">{error}</p>
			<Button class="mt-4" variant="outline" onclick={() => fetchData(days)}>Retry</Button>
		</div>
	{:else if equityData.length < 2}
		<div class="flex flex-col items-center justify-center py-16 text-center">
			<LineChart class="h-12 w-12 text-muted-foreground mb-4" />
			<h2 class="text-lg font-semibold">Not Enough Data</h2>
			<p class="text-sm text-muted-foreground mt-2 max-w-[320px]">At least 2 days of trading history are needed to display the equity curve.</p>
		</div>
	{:else}
		<section>
			<h2 class="text-lg font-semibold mb-4">Equity Curve</h2>
			<EquityChart data={equityData} />
		</section>

		<section>
			<h2 class="text-lg font-semibold mb-4">Drawdown</h2>
			<DrawdownChart data={drawdownData} />
		</section>
	{/if}
</div>
