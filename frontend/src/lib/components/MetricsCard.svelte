<script lang="ts">
	import { Card, CardContent, CardHeader } from '$lib/components/ui/card/index.js';
	import { Root, Trigger, Content } from '$lib/components/ui/tooltip/index.js';
	import Info from '@lucide/svelte/icons/info';
	import type { Snippet } from 'svelte';

	let {
		label,
		value,
		tooltip = '',
		children
	}: {
		label: string;
		value: string;
		tooltip?: string;
		children?: Snippet;
	} = $props();
</script>

<Card class="min-w-[200px]">
	<CardHeader class="pb-2">
		<div class="flex items-center gap-1.5">
			<span class="text-xs font-semibold text-muted-foreground uppercase tracking-wide">{label}</span>
			{#if tooltip}
				<Root delayDuration={200}>
					<Trigger>
						<Info class="h-3.5 w-3.5 text-muted-foreground" />
					</Trigger>
					<Content side="top" class="max-w-[240px] text-xs">
						{tooltip}
					</Content>
				</Root>
			{/if}
		</div>
	</CardHeader>
	<CardContent>
		<span class="text-3xl font-semibold font-tabular text-foreground">{value}</span>
		{#if children}
			<div class="mt-1">
				{@render children()}
			</div>
		{/if}
	</CardContent>
</Card>
