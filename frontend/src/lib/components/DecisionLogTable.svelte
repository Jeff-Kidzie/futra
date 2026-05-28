<script lang="ts">
	import type { Decision } from '$lib/types';
	import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '$lib/components/ui/table/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import BrainCircuit from '@lucide/svelte/icons/brain-circuit';

	let {
		decisions = [],
		loading = false
	}: {
		decisions: Decision[];
		loading: boolean;
	} = $props();

	let expandedRows = $state<Set<number>>(new Set());
	let expanded: number[] = $derived([...expandedRows]);

	function toggleExpand(index: number) {
		const next = new Set(expandedRows);
		if (next.has(index)) {
			next.delete(index);
		} else {
			next.add(index);
		}
		expandedRows = next;
	}

	function formatTimestamp(iso: string): string {
		const d = new Date(iso);
		return d.toISOString().replace('T', ' ').substring(0, 19);
	}

	function regimeBadgeClass(regime: string): string {
		switch (regime) {
			case 'trending': return 'bg-blue-300/10 text-blue-300 border-blue-300/20';
			case 'ranging': return 'bg-orange-400/10 text-orange-400 border-orange-400/20';
			case 'volatile': return 'bg-red-400/10 text-red-400 border-red-400/20';
			case 'quiet': return 'bg-gray-400/10 text-gray-400 border-gray-400/20';
			default: return '';
		}
	}

	function regimeLabel(regime: string): string {
		return regime.charAt(0).toUpperCase() + regime.slice(1);
	}
</script>

{#if loading}
	<div class="space-y-2">
		{#each Array(8) as _}
			<Skeleton class="h-10 w-full rounded-md" />
		{/each}
	</div>
{:else if decisions.length === 0}
	<div class="flex flex-col items-center justify-center py-16 text-center">
		<BrainCircuit class="h-12 w-12 text-muted-foreground mb-4" />
		<h2 class="text-lg font-semibold">No AI Decisions Yet</h2>
		<p class="text-sm text-muted-foreground mt-2 max-w-[320px]">AI decision logs will appear here once the engine analyzes market conditions and adjusts parameters.</p>
	</div>
{:else}
	<div class="overflow-x-auto">
		<Table>
			<TableHeader>
				<TableRow>
					<TableHead>Time</TableHead>
					<TableHead>Symbol</TableHead>
					<TableHead>Timeframe</TableHead>
					<TableHead class="text-center">Regime</TableHead>
					<TableHead class="text-right">Confidence</TableHead>
					<TableHead class="text-right">SL Pips</TableHead>
					<TableHead class="text-right">TP Pips</TableHead>
					<TableHead class="text-right">Lot Size</TableHead>
					<TableHead class="text-center">Actions</TableHead>
				</TableRow>
			</TableHeader>
			<TableBody>
				{#each decisions as decision, i}
					<TableRow class="cursor-pointer" onclick={() => toggleExpand(i)} role="button" tabindex="0" aria-expanded={expandedRows.has(i)} aria-controls="reasoning-{i}">
						<TableCell class="px-4 py-2">{formatTimestamp(decision.timestamp)}</TableCell>
						<TableCell class="px-4 py-2">{decision.symbol}</TableCell>
						<TableCell class="px-4 py-2">{decision.timeframe}</TableCell>
						<TableCell class="px-4 py-2 text-center">
							<Badge variant="outline" class={regimeBadgeClass(decision.regime)}>
								{regimeLabel(decision.regime)}
							</Badge>
						</TableCell>
						<TableCell class="px-4 py-2 text-right font-tabular">{Math.round(decision.confidence * 100)}%</TableCell>
						<TableCell class="px-4 py-2 text-right font-tabular">{decision.sl_pips.toFixed(1)}</TableCell>
						<TableCell class="px-4 py-2 text-right font-tabular">{decision.tp_pips.toFixed(1)}</TableCell>
						<TableCell class="px-4 py-2 text-right font-tabular">{decision.lot_size.toFixed(2)}</TableCell>
						<TableCell class="px-4 py-2 text-center">
							<Button variant="ghost" size="sm" onclick={(e: MouseEvent) => { e.stopPropagation(); toggleExpand(i); }}>
								{expandedRows.has(i) ? 'Hide Reasoning' : 'Show Reasoning'}
							</Button>
						</TableCell>
					</TableRow>
					{#if expandedRows.has(i)}
						<TableRow id="reasoning-{i}">
							<TableCell colspan="9" class="px-4 py-3 bg-muted/30">
								<p class="text-sm text-muted-foreground whitespace-pre-wrap">{decision.reasoning}</p>
							</TableCell>
						</TableRow>
					{/if}
				{/each}
			</TableBody>
		</Table>
	</div>
{/if}
