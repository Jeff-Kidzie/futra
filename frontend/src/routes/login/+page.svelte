<script lang="ts">
	import { goto } from '$app/navigation';
	import { login } from '$lib/api';
	import { isAuthenticated } from '$lib/stores';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '$lib/components/ui/card/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		error = '';

		if (!username || !password) {
			error = 'Invalid username or password. Please try again.';
			return;
		}

		loading = true;
		try {
			await login(username, password);
			isAuthenticated.set(true);
			await goto('/');
		} catch {
			error = 'Invalid username or password. Please try again.';
		} finally {
			loading = false;
		}
	}
</script>

<div class="flex h-screen items-center justify-center p-4">
	<Card class="w-full max-w-[400px]">
		<CardHeader class="text-center">
			<CardTitle class="text-xl">Futra Dashboard</CardTitle>
			<CardDescription>Sign In</CardDescription>
		</CardHeader>
		<CardContent>
			<form onsubmit={handleSubmit} class="space-y-4">
				<div class="space-y-2">
					<Label for="username">Username</Label>
					<Input
						id="username"
						type="text"
						placeholder="Enter your username"
						bind:value={username}
						aria-required="true"
						aria-invalid={error ? 'true' : undefined}
						disabled={loading}
					/>
				</div>
				<div class="space-y-2">
					<Label for="password">Password</Label>
					<Input
						id="password"
						type="password"
						placeholder="Enter your password"
						bind:value={password}
						aria-required="true"
						aria-invalid={error ? 'true' : undefined}
						disabled={loading}
					/>
				</div>

				{#if error}
					<p class="text-sm text-red-400" role="alert">{error}</p>
				{/if}

				<Button type="submit" class="w-full" disabled={loading}>
					{#if loading}
						<Spinner class="mr-2 h-4 w-4" />
						Signing in...
					{:else}
						Sign In
					{/if}
				</Button>
			</form>
		</CardContent>
	</Card>
</div>
