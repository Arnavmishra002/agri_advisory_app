// CLEAN UI SCRIPT FOR KRISHIMITRA AI - NO SYNTAX ERRORS
console.log('🚀 Clean UI Script Loading...');

// Global variables
let currentLocation = { lat: 28.6139, lon: 77.2090, name: 'Delhi' };

// Simple service show function
function showService(serviceName) {
    try {
        console.log('Showing service:', serviceName);
        
        // Hide all service contents
        document.querySelectorAll('.service-content').forEach(content => {
            content.style.display = 'none';
            content.classList.remove('active');
        });
        
        // Show the selected service
        const content = document.getElementById(serviceName + '-content');
        if (content) {
            content.style.display = 'block';
            content.classList.add('active');
            content.scrollIntoView({ behavior: 'smooth' });
            console.log('✅ Service shown:', serviceName);
        } else {
            console.error('Content not found:', serviceName);
        }
    } catch (error) {
        console.error('Error in showService:', error);
    }
}

// Initialize service cards
function initServiceCards() {
    console.log('🎯 Initializing Service Cards...');
    
    const serviceCards = document.querySelectorAll('.service-card[data-service]');
    console.log('Found service cards:', serviceCards.length);
    
    serviceCards.forEach((card, index) => {
        const serviceName = card.getAttribute('data-service');
        
        // Make card clickable
        card.style.cursor = 'pointer';
        
        // Add click handler
        card.onclick = function(e) {
            e.preventDefault();
            console.log('Card clicked:', serviceName);
            showService(serviceName);
        };
        
        console.log(`Card ${index + 1} (${serviceName}) initialized`);
    });
}

// Test function
function testJavaScript() {
    alert('JavaScript is working! ✅\n\nService cards should be clickable now!');
    
    // Test first service card
    const serviceCards = document.querySelectorAll('.service-card[data-service]');
    if (serviceCards.length > 0) {
        const firstCard = serviceCards[0];
        const serviceName = firstCard.getAttribute('data-service');
        showService(serviceName);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM Content Loaded - Initializing Clean UI...');
    
    // Initialize service cards
    initServiceCards();
    
    // Set default location
    const locationInput = document.getElementById('locationSearchInput');
    if (locationInput) {
        locationInput.value = 'Delhi';
    }
    
    console.log('🎉 Clean UI Initialization Complete');
});

// Make testJavaScript available globally
window.testJavaScript = testJavaScript;


