<script lang="ts">
	import { wsConnected } from '$lib/stores';
	import { Root, Trigger, Content } from '$lib/components/ui/tooltip/index.js';
</script>

<Root delayDuration={200}>
	<Trigger>
		<div
			class="connection-status"
			class:connected={$wsConnected}
			class:disconnected={!$wsConnected}
			class:connection-pulse={$wsConnected}
			role="status"
			aria-label={$wsConnected ? 'WebSocket connected' : 'WebSocket disconnected'}
		></div>
	</Trigger>
	<Content side="right">
		{$wsConnected ? 'Connected' : 'Disconnected — retrying'}
	</Content>
</Root>

<style>
	.connection-status {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		border: 2px solid var(--card);
	}
	.connection-status.connected {
		background-color: #00E676;
	}
	.connection-status.disconnected {
		background-color: #FF5252;
	}
</style>
