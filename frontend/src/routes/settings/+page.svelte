<script lang="ts">
	import { onMount } from 'svelte';
	import { getStrategy, logout } from '$lib/api';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '$lib/components/ui/dialog/index.js';
	import type { StrategyConfig } from '$lib/types';

	let strategy = $state<StrategyConfig | null>(null);
	let strategyLoading = $state(true);
	let strategyError = $state('');
	let logoutOpen = $state(false);

	onMount(async () => {
		try {
			const data = await getStrategy();
			strategy = data;
		} catch (e: unknown) {
			strategyError = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			strategyLoading = false;
		}
	});
</script>

<div class="space-y-8 max-w-2xl">
	<h1 class="text-xl font-semibold">Settings</h1>

	<!-- Strategy Configuration -->
	<section class="space-y-3">
		<h2 class="text-lg font-semibold">Strategy Configuration</h2>
		<p class="text-sm text-muted-foreground">Current strategy parameters (read-only).</p>
		{#if strategyLoading}
			<div class="bg-muted rounded-md p-4">
				<p class="text-sm text-muted-foreground">Loading...</p>
			</div>
		{:else if strategyError}
			<div class="bg-muted rounded-md p-4">
				<p class="text-sm text-muted-foreground">Unable to load strategy configuration.</p>
			</div>
		{:else if strategy}
			<pre class="bg-muted rounded-md p-4 overflow-x-auto text-sm font-mono"><code>{JSON.stringify(strategy.config, null, 2)}</code></pre>
		{:else}
			<div class="bg-muted rounded-md p-4">
				<p class="text-sm text-muted-foreground">No strategy configuration available.</p>
			</div>
		{/if}
	</section>

	<!-- Session -->
	<section class="space-y-3">
		<h2 class="text-lg font-semibold">Session</h2>
		<Button variant="destructive" onclick={() => logoutOpen = true}>Log Out</Button>

		<Dialog open={logoutOpen}>
			<DialogContent>
				<DialogHeader>
					<DialogTitle>Log Out</DialogTitle>
					<DialogDescription>Are you sure you want to log out? You will need to sign in again to access the dashboard.</DialogDescription>
				</DialogHeader>
				<DialogFooter>
					<Button variant="outline" onclick={() => logoutOpen = false}>Stay Signed In</Button>
					<Button variant="destructive" onclick={() => { logout(); }}>Log Out</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	</section>
</div>
