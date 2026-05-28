<script lang="ts">
	import { onMount } from 'svelte';
	import { createChart, AreaSeries, type IChartApi, type Time, ColorType } from 'lightweight-charts';
	import type { EquityPoint } from '$lib/types';

	let {
		data = []
	}: {
		data: EquityPoint[];
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
			height: 400,
		});

		const series = chart.addSeries(AreaSeries, {
			lineColor: '#2962FF',
			topColor: 'rgba(41, 98, 255, 0.15)',
			bottomColor: 'rgba(41, 98, 255, 0.05)',
			lineWidth: 2,
		});

		if (data.length > 0) {
			series.setData(data.map(d => ({ time: d.time as Time, value: d.value })));
		}

		const observer = new ResizeObserver(() => {
			if (chart && container) {
				chart.resize(container.clientWidth, 400);
			}
		});
		observer.observe(container);

		return () => {
			observer.disconnect();
			chart?.remove();
		};
	});
</script>

<div bind:this={container} class="w-full h-[400px]"></div>

<!-- Accessible data table for screen readers -->
<table class="sr-only" aria-label="Equity curve data">
	<thead>
		<tr>
			<th scope="col">Date</th>
			<th scope="col">Equity</th>
		</tr>
	</thead>
	<tbody>
		{#each data as point}
			<tr>
				<td>{point.time}</td>
				<td>${point.value.toFixed(2)}</td>
			</tr>
		{/each}
	</tbody>
</table>
