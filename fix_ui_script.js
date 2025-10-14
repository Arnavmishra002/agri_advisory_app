// Simplified UI Fix Script for Krishimitra AI
// This script replaces the problematic JavaScript in index.html

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Simple UI Fix Script Loaded');
    
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
            console.error('Error showing service:', error);
        }
    }
    
    // Initialize service cards
    function initServiceCards() {
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
    window.testJavaScript = function() {
        alert('JavaScript is working! ✅\n\nService cards should be clickable now.');
        initServiceCards();
    };
    
    // Initialize everything
    initServiceCards();
    
    console.log('🎉 UI Fix Script Complete');
});



