<script lang="ts">
	import { onMount } from 'svelte';
	import { createChart, AreaSeries, LineSeries, type IChartApi, type Time, ColorType } from 'lightweight-charts';
	import type { DrawdownPoint } from '$lib/types';

	let {
		data = []
	}: {
		data: DrawdownPoint[];
	} = $props();

	let container: HTMLDivElement;
	let chart: IChartApi | null = $state(null);

	onMount(() => {
		if (!container) return;

		chart = createChart(container, {
			layout: {
				background: { type: ColorType.Solid, color: 'transparent' },
				textColor: '#8C8C9E',
			},
			grid: {
				vertLines: { color: 'rgba(140, 140, 158, 0.1)' },
				horzLines: { color: 'rgba(140, 140, 158, 0.1)' },
			},
			timeScale: { timeVisible: true },
			crosshair: {
				vertLine: { color: 'rgba(235, 235, 240, 0.4)' },
				horzLine: { color: 'rgba(235, 235, 240, 0.4)' },
			},
			width: container.clientWidth,
			height: 248,
		});

		// Drawdown area series (red fill below zero)
		chart.addSeries(AreaSeries, {
			lineColor: '#FF5252',
			topColor: 'rgba(255, 82, 82, 0.05)',
			bottomColor: 'rgba(255, 82, 82, 0.3)',
			lineWidth: 2,
		}).setData(data.map(d => ({ time: d.time as Time, value: d.value })));

		// Dashed zero line
		chart.addSeries(LineSeries, {
			color: 'rgba(140, 140, 158, 0.5)',
			lineWidth: 1,
			lineStyle: 2,
		}).setData(data.map(d => ({ time: d.time as Time, value: 0 })));

		const observer = new ResizeObserver(() => {
			if (chart && container) {
				chart.resize(container.clientWidth, 248);
			}
		});
		observer.observe(container);

		return () => {
			observer.disconnect();
			chart?.remove();
		};
	});
</script>

<div bind:this={container} class="w-full h-[248px]"></div>

<!-- Accessible data table for screen readers -->
<table class="sr-only" aria-label="Drawdown data">
	<thead>
		<tr>
			<th scope="col">Date</th>
			<th scope="col">Drawdown</th>
		</tr>
	</thead>
	<tbody>
		{#each data as point}
			<tr>
				<td>{point.time}</td>
				<td>{point.value.toFixed(2)}%</td>
			</tr>
		{/each}
	</tbody>
</table>
