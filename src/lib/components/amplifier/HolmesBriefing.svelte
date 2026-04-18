<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { slide } from 'svelte/transition';

	let loading = false;
	let briefingContent: string | null = null;
	let showPanel = false;
	let pollingInterval: ReturnType<typeof setInterval> | null = null;
	let pollCount = 0;
	const MAX_POLLS = 30; // 2.5 min at 5s intervals

	async function triggerHolmes() {
		if (loading) return;

		// First check if today's briefing already exists
		try {
			const existing = await fetch('/api/amplifier/daily-note', { credentials: 'include' });
			if (existing.ok) {
				const data = await existing.json();
				if (data.holmes_section) {
					briefingContent = data.holmes_section;
					showPanel = true;
					return;
				}
			}
		} catch {}

		// No existing briefing — trigger Holmes
		loading = true;
		pollCount = 0;

		try {
			const res = await fetch('/api/amplifier/holmes-briefing', {
				method: 'POST',
				credentials: 'include'
			});

			if (!res.ok) {
				const err = await res.json().catch(() => ({}));
				throw new Error(err.detail || `Error ${res.status}`);
			}

			toast.info('Holmes is scanning the web — results in ~2 minutes');
			startPolling();
		} catch (e: any) {
			toast.error(`Holmes error: ${e.message}`);
			loading = false;
		}
	}

	function startPolling() {
		pollingInterval = setInterval(async () => {
			pollCount++;
			if (pollCount > MAX_POLLS) {
				stopPolling();
				toast.error('Holmes scan timed out — check Telegram for results');
				return;
			}
			try {
				const res = await fetch('/api/amplifier/daily-note', { credentials: 'include' });
				if (!res.ok) return;
				const data = await res.json();
				if (data.holmes_section) {
					stopPolling();
					briefingContent = data.holmes_section;
					showPanel = true;
					toast.success('Morning briefing ready');
				}
			} catch {}
		}, 5000);
	}

	function stopPolling() {
		if (pollingInterval) {
			clearInterval(pollingInterval);
			pollingInterval = null;
		}
		loading = false;
	}

	function pasteToChat() {
		if (!briefingContent) return;
		// Use Open WebUI's postMessage protocol to set the chat input
		window.postMessage({ type: 'input:prompt', text: briefingContent }, '*');
		const chatInput = document.getElementById('chat-input');
		chatInput?.focus();
		toast.success('Briefing pasted to chat input');
	}

	onMount(() => {
		return () => stopPolling();
	});
</script>

<!-- Morning Briefing trigger button -->
<button
	class="group grow flex items-center space-x-3 rounded-2xl px-2.5 py-2
		hover:bg-gray-100 dark:hover:bg-gray-900 transition outline-none
		disabled:opacity-40 disabled:cursor-not-allowed"
	on:click={triggerHolmes}
	disabled={loading}
	title="Run Holmes morning intelligence scan"
>
	<div class="self-center">
		{#if loading}
			<svg class="animate-spin size-4.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
				<path class="opacity-75" fill="currentColor"
					d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
			</svg>
		{:else}
			<svg class="size-4.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
				<path stroke-linecap="round" stroke-linejoin="round"
					d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
			</svg>
		{/if}
	</div>

	<div class="flex flex-1 self-center translate-y-[0.5px]">
		<div class="self-center text-sm font-primary">
			{#if loading}
				Scanning...
			{:else}
				Morning Briefing
			{/if}
		</div>
	</div>

	{#if briefingContent && !loading}
		<div class="size-2 rounded-full bg-green-500 shrink-0" title="Briefing ready"></div>
	{/if}
</button>

<!-- Briefing results panel -->
{#if showPanel && briefingContent}
	<div
		class="mx-2 mt-1 mb-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden shadow-sm"
		transition:slide={{ duration: 200 }}
	>
		<div class="flex items-center justify-between px-3 py-2 border-b border-gray-100 dark:border-gray-800">
			<span class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
				Holmes Dossier
			</span>
			<div class="flex gap-1">
				<button
					class="text-xs px-2 py-0.5 rounded-md bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 transition"
					on:click={pasteToChat}
					title="Paste to chat input"
				>
					Use in chat
				</button>
				<button
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition px-1"
					on:click={() => (showPanel = false)}
					title="Close"
				>
					<svg class="size-3.5" viewBox="0 0 20 20" fill="currentColor">
						<path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
					</svg>
				</button>
			</div>
		</div>
		<div class="px-3 py-2 max-h-64 overflow-y-auto scrollbar-hidden">
			<pre class="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono leading-relaxed">{briefingContent}</pre>
		</div>
	</div>
{/if}
