<script lang="ts">
	import { onMount } from 'svelte';
	import { getPositions, getAccount, getAlerts } from '$lib/api';
	import { positions, account, alerts } from '$lib/stores';
	import AccountSummary from '$lib/components/AccountSummary.svelte';
	import PositionsTable from '$lib/components/PositionsTable.svelte';
	import AlertFeed from '$lib/components/AlertFeed.svelte';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import AlertTriangle from '@lucide/svelte/icons/alert-triangle';
	import { Button } from '$lib/components/ui/button/index.js';

	let loading = $state(true);
	let error = $state('');

	onMount(async () => {
		try {
			const [pos, acc, alrt] = await Promise.all([
				getPositions(), getAccount(), getAlerts(false)
			]);
			positions.set(pos);
			account.set(acc);
			alerts.set(alrt);
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	});
</script>

<div class="space-y-6">
	<h1 class="text-xl font-semibold">Dashboard</h1>

	{#if loading}
		<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
			{#each Array(4) as _}
				<Skeleton class="h-[120px] w-full rounded-md" />
			{/each}
		</div>
	{:else if error}
		<div class="flex flex-col items-center justify-center py-12 text-center">
			<AlertTriangle class="h-12 w-12 text-destructive mb-4" />
			<h2 class="text-lg font-semibold">Unable to Load Data</h2>
			<p class="text-sm text-muted-foreground mt-2">Something went wrong while fetching dashboard data.</p>
			<Button class="mt-4" variant="outline" onclick={() => window.location.reload()}>Retry</Button>
		</div>
	{:else}
		<AccountSummary />

		<section>
			<h2 class="text-lg font-semibold mb-4">Open Positions</h2>
			<PositionsTable />
		</section>

		<section>
			<h2 class="text-lg font-semibold mb-4">Recent Alerts</h2>
			<AlertFeed />
		</section>
	{/if}
</div>
