<script lang="ts">
	import { onMount } from 'svelte';
	import { getDecisions } from '$lib/api';
	import DecisionLogTable from '$lib/components/DecisionLogTable.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import type { Decision } from '$lib/types';

	let decisions = $state<Decision[]>([]);
	let loading = $state(true);
	let error = $state('');
	let offset = $state(0);
	const pageSize = 50;

	async function fetchDecisions(newOffset = 0) {
		loading = true;
		error = '';
		try {
			const data = await getDecisions(pageSize, newOffset);
			decisions = data;
			offset = newOffset;
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		fetchDecisions();
	});
</script>

<div class="space-y-6">
	<h1 class="text-xl font-semibold">AI Decisions</h1>

	{#if error}
		<div class="flex flex-col items-center justify-center py-12 text-center">
			<h2 class="text-lg font-semibold">Unable to Load Data</h2>
			<p class="text-sm text-muted-foreground mt-2">{error}</p>
			<Button class="mt-4" variant="outline" onclick={() => fetchDecisions()}>Retry</Button>
		</div>
	{:else}
		<DecisionLogTable {decisions} {loading} />

		<div class="flex justify-center gap-2 mt-4">
			<Button variant="outline" size="sm" disabled={offset === 0 || loading} onclick={() => fetchDecisions(offset - pageSize)}>
				Previous
			</Button>
			<Button variant="outline" size="sm" disabled={decisions.length < pageSize || loading} onclick={() => fetchDecisions(offset + pageSize)}>
				Next
			</Button>
		</div>
	{/if}
</div>
