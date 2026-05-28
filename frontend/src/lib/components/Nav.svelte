<script lang="ts">
	import { page } from '$app/stores';
	import { Sidebar, SidebarContent, SidebarGroup, SidebarGroupLabel, SidebarMenu, SidebarMenuItem, SidebarMenuButton } from '$lib/components/ui/sidebar/index.js';
	import ConnectionStatus from './ConnectionStatus.svelte';
	import LayoutDashboard from '@lucide/svelte/icons/layout-dashboard';
	import ListOrdered from '@lucide/svelte/icons/list-ordered';
	import BrainCircuit from '@lucide/svelte/icons/brain-circuit';
	import LineChart from '@lucide/svelte/icons/line-chart';
	import Bell from '@lucide/svelte/icons/bell';
	import Settings from '@lucide/svelte/icons/settings';
	import { Separator } from '$lib/components/ui/separator/index.js';

	const navItems = [
		{ label: 'Home', href: '/', icon: LayoutDashboard },
		{ label: 'Trade History', href: '/trades', icon: ListOrdered },
		{ label: 'AI Decisions', href: '/decisions', icon: BrainCircuit },
		{ label: 'Performance', href: '/performance', icon: LineChart },
		{ label: 'Alerts', href: '/alerts', icon: Bell },
		{ label: 'Settings', href: '/settings', icon: Settings },
	];
</script>

<Sidebar>
	<SidebarContent>
		<SidebarGroup>
			<SidebarGroupLabel>Futra Dashboard</SidebarGroupLabel>
			<SidebarMenu>
				{#each navItems as item}
					<SidebarMenuItem>
						<SidebarMenuButton href={item.href} isActive={$page.url.pathname === item.href}>
							<item.icon class="h-5 w-5" />
							<span>{item.label}</span>
						</SidebarMenuButton>
					</SidebarMenuItem>
				{/each}
			</SidebarMenu>
		</SidebarGroup>
		<Separator />
		<div class="flex justify-center p-4">
			<ConnectionStatus />
		</div>
	</SidebarContent>
</Sidebar>
