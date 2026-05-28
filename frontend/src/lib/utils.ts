import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

// Utility types used by shadcn-svelte components
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export type WithElementRef<T, _R = HTMLElement> = T & { el?: HTMLElement };
export type WithoutChildren<T> = Omit<T, 'children'>;
export type WithoutChildrenOrChild<T> = Omit<T, 'children' | 'child'>;
