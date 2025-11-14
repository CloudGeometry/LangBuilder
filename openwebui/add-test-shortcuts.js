// Script to add test shortcuts to OpenWebUI
// Run this in your browser console on the OpenWebUI page

(async function addTestShortcuts() {
    console.log('🚀 Adding test shortcuts...');

    // Fetch current settings
    const response = await fetch('/api/v1/users/user/settings', {
        headers: {
            'Authorization': 'Bearer ' + localStorage.token,
            'Content-Type': 'application/json'
        }
    });

    const currentSettings = await response.json();
    console.log('📋 Current settings:', currentSettings);

    // Create test shortcuts
    const testShortcuts = [
        {
            id: crypto.randomUUID(),
            functionId: 'test-function-1',
            title: 'Data Analysis',
            description: 'Analyze data with AI',
            icon: '📊',
            color: 'rgba(59, 130, 246, 0.15)',
            prompt: '',
            autoSubmit: false,
            enabled: true,
            order: 0
        },
        {
            id: crypto.randomUUID(),
            functionId: 'test-function-2',
            title: 'Code Review',
            description: 'Review code quality',
            icon: '🔍',
            color: 'rgba(34, 197, 94, 0.15)',
            prompt: '',
            autoSubmit: false,
            enabled: true,
            order: 1
        },
        {
            id: crypto.randomUUID(),
            functionId: 'test-function-3',
            title: 'Write Content',
            description: 'Generate content',
            icon: '✍️',
            color: 'rgba(168, 85, 247, 0.15)',
            prompt: '',
            autoSubmit: false,
            enabled: true,
            order: 2
        },
        {
            id: crypto.randomUUID(),
            functionId: 'test-function-1',
            title: 'Debug Code',
            description: 'Find and fix bugs',
            icon: '🐛',
            color: 'rgba(239, 68, 68, 0.15)',
            prompt: '',
            autoSubmit: false,
            enabled: true,
            order: 3
        }
    ];

    // Update settings with shortcuts enabled
    const updatedSettings = {
        ...currentSettings,
        flowShortcuts: {
            enabled: true,
            layout: '2x2',
            shortcuts: testShortcuts
        }
    };

    console.log('💾 Saving settings with shortcuts:', updatedSettings.flowShortcuts);

    // Save to database
    const saveResponse = await fetch('/api/v1/users/user/settings/update', {
        method: 'POST',
        headers: {
            'Authorization': 'Bearer ' + localStorage.token,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(updatedSettings)
    });

    if (!saveResponse.ok) {
        console.error('❌ Failed to save:', await saveResponse.text());
        return;
    }

    const result = await saveResponse.json();
    console.log('✅ Shortcuts added successfully!', result);
    console.log('🔄 Please refresh the page to see your shortcuts');

    return result;
})();
