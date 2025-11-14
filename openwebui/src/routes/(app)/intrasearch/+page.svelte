<script lang="ts">
	import { page } from '$app/stores';
	import { v4 as uuidv4 } from 'uuid';
	import { onMount } from 'svelte';
	// Import the NEW independent IntraSearch component (no LLM dependencies)
	import IntraSearchChatNew from '$lib/components/intrasearch/IntraSearchChatNew.svelte';

	// Generate a unique session ID for IntraSearch
	let sessionId = '';

	onMount(() => {
		// Create a new unique session ID for this IntraSearch session
		sessionId = uuidv4();
	});
</script>

<svelte:head>
	<title>IntraSearch - Enterprise Internal Search</title>
</svelte:head>

{#if sessionId}
	<IntraSearchChatNew chatIdProp={sessionId} />
{/if}