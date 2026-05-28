<script lang="ts">
	import { alerts } from '$lib/stores';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import BellOff from '@lucide/svelte/icons/bell-off';

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
</script>

{#if $alerts.length === 0}
	<div class="flex flex-col items-center justify-center py-12 text-center">
		<BellOff class="h-12 w-12 text-muted-foreground mb-4" />
		<h2 class="text-lg font-semibold">All Clear</h2>
		<p class="text-sm text-muted-foreground mt-2 max-w-[320px]">No active alerts. You'll be notified here when critical events occur.</p>
	</div>
{:else}
	<div class="space-y-2">
		{#each $alerts.slice(0, 5) as alert}
			<div class="flex items-center gap-3 p-3 rounded-md border border-border bg-card">
				<Badge variant="outline" class={severityBadgeClass(alert.severity)}>
					{alert.severity.charAt(0).toUpperCase() + alert.severity.slice(1)}
				</Badge>
				<span class="text-sm flex-1">{alert.message}</span>
				<span class="text-xs text-muted-foreground">{relativeTime(alert.created_at)}</span>
			</div>
		{/each}
	</div>
{/if}
