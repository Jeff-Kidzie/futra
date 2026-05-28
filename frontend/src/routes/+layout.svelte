<script lang="ts">
	import '../app.css';
	import { page } from '$app/stores';
	import { isAuthenticated } from '$lib/stores';
	import Nav from '$lib/components/Nav.svelte';
	import { onMount } from 'svelte';
	import { Toaster } from '$lib/components/ui/sonner/index.js';

	let { children } = $props();

	onMount(() => {
		const token = localStorage.getItem('futra_token');
		isAuthenticated.set(!!token);
	});
</script>

<svelte:head>
	<link rel="icon" href="/favicon.svg" />
</svelte:head>

{#if String($page.url.pathname) === '/login'}
	{@render children()}
{:else if $isAuthenticated}
	<div class="flex h-screen">
		<Nav />
		<main class="flex-1 overflow-y-auto p-6 ml-60 max-md:ml-0">
			{@render children()}
		</main>
	</div>
	<Toaster />
{:else}
	<div class="flex h-screen items-center justify-center">
		<p class="text-muted-foreground">Redirecting to login...</p>
	</div>
{/if}
