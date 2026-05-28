<script lang="ts">
	import { onMount } from 'svelte';
	import { getAlerts, acknowledgeAlert } from '$lib/api';
	import { alerts } from '$lib/stores';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '$lib/components/ui/dialog/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import BellOff from '@lucide/svelte/icons/bell-off';
	import CheckSquare from '@lucide/svelte/icons/check-square';
	import type { Alert } from '$lib/types';

	let loading = $state(true);
	let error = $state('');
	let activeTab = $state('all');
	let confirmOpen = $state(false);

	function relativeTime(iso: string): string {
		const now = Date.now();
		const then = new Date(iso).getTime();
		const diff = Math.floor((now - then) / 1000);
		if (diff < 60) return 'just now';
		if (diff < 3600) return `${Math.floor(diff / 60)} minutes ago`;
		if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
		return `${Math.floor(diff / 86400)} days ago`;
	}

	function severityBadgeClass(severity: string): string {
		switch (severity) {
			case 'critical': return 'bg-red-500/10 text-red-400 border-red-500/20';
			case 'warning': return 'bg-orange-400/10 text-orange-400 border-orange-400/20';
			case 'info': return 'bg-blue-300/10 text-blue-300 border-blue-300/20';
			default: return '';
		}
	}

	const filteredAlerts = $derived(
		$alerts.filter(a => {
			if (activeTab === 'unacknowledged') return !a.acknowledged;
			if (activeTab === 'critical') return a.severity === 'critical';
			return true;
		})
	);

	async function fetchAlerts() {
		loading = true;
		error = '';
		try {
			const data = await getAlerts();
			alerts.set(data);
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	async function handleAcknowledge(id: number) {
		try {
			await acknowledgeAlert(id);
			alerts.update(a => a.filter(alert => alert.id !== id));
		} catch {
			// silently fail
		}
	}

	async function acknowledgeAll() {
		const unacknowledged = $alerts.filter(a => !a.acknowledged);
		for (const alert of unacknowledged) {
			await handleAcknowledge(alert.id);
		}
		confirmOpen = false;
	}

	function capitalize(s: string): string {
		return s.charAt(0).toUpperCase() + s.slice(1);
	}

	onMount(() => {
		fetchAlerts();
	});
</script>

<div class="space-y-6">
	<div class="flex items-center justify-between">
		<h1 class="text-xl font-semibold">Alerts</h1>
		<Button variant="outline" disabled={$alerts.filter(a => !a.acknowledged).length === 0} onclick={() => confirmOpen = true}>
			<CheckSquare class="h-4 w-4 mr-2" />
			Acknowledge All
		</Button>

		<Dialog open={confirmOpen}>
			<DialogContent>
				<DialogHeader>
					<DialogTitle>Acknowledge All</DialogTitle>
					<DialogDescription>Mark all alerts as acknowledged?</DialogDescription>
				</DialogHeader>
				<DialogFooter>
					<Button variant="outline" onclick={() => confirmOpen = false}>Cancel</Button>
					<Button onclick={acknowledgeAll}>Acknowledge</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	</div>

	<!-- Filter tabs -->
	<div class="flex gap-2">
		<Button variant={activeTab === 'all' ? 'default' : 'outline'} size="sm" onclick={() => activeTab = 'all'}>All</Button>
		<Button variant={activeTab === 'unacknowledged' ? 'default' : 'outline'} size="sm" onclick={() => activeTab = 'unacknowledged'}>Unacknowledged</Button>
		<Button variant={activeTab === 'critical' ? 'default' : 'outline'} size="sm" onclick={() => activeTab = 'critical'}>Critical</Button>
	</div>

	{#if loading}
		<div class="space-y-2">
			{#each Array(8) as _}
				<Skeleton class="h-14 w-full rounded-md" />
			{/each}
		</div>
	{:else if error}
		<div class="flex flex-col items-center justify-center py-12 text-center">
			<h2 class="text-lg font-semibold">Unable to Load Data</h2>
			<p class="text-sm text-muted-foreground mt-2">{error}</p>
			<Button class="mt-4" variant="outline" onclick={fetchAlerts}>Retry</Button>
		</div>
	{:else if filteredAlerts.length === 0}
		<div class="flex flex-col items-center justify-center py-16 text-center">
			<BellOff class="h-12 w-12 text-muted-foreground mb-4" />
			<h2 class="text-lg font-semibold">All Clear</h2>
			<p class="text-sm text-muted-foreground mt-2 max-w-[320px]">No active alerts. You'll be notified here when critical events occur.</p>
		</div>
	{:else}
		<div class="space-y-2">
			{#each filteredAlerts as alert}
				<div class="flex items-center gap-3 p-3 rounded-md border border-border bg-card">
					<Badge variant="outline" class={severityBadgeClass(alert.severity)}>
						{capitalize(alert.severity)}
					</Badge>
					<span class="text-sm flex-1">{alert.message}</span>
					<span class="text-xs text-muted-foreground">{relativeTime(alert.created_at)}</span>
					{#if !alert.acknowledged}
						<Button variant="ghost" size="sm" onclick={() => handleAcknowledge(alert.id)}>Acknowledge</Button>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>
