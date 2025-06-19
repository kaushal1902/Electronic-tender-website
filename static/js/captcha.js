document.addEventListener('DOMContentLoaded', function() {
    const captchaContainer = document.querySelector('.captcha-container');
    const captchaText = document.querySelector('.captcha-text');
    const refreshButton = document.getElementById('refresh-captcha');
    
    if (captchaContainer && refreshButton) {
        // Add random lines and dots to make captcha more complex
        addNoise(captchaContainer);
        
        // Refresh captcha when button is clicked
        refreshButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Make AJAX request to get new captcha
            fetch('/refresh-captcha', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.captcha) {
                    captchaText.textContent = data.captcha;
                    
                    // Clear previous noise and add new
                    clearNoise(captchaContainer);
                    addNoise(captchaContainer);
                }
            })
            .catch(error => console.error('Error refreshing captcha:', error));
        });
    }
    
    // Add visual noise to captcha
    function addNoise(container) {
        // Create a canvas element for drawing lines and dots
        const canvas = document.createElement('canvas');
        canvas.width = container.offsetWidth;
        canvas.height = container.offsetHeight;
        canvas.style.position = 'absolute';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.pointerEvents = 'none'; // Make sure it doesn't interfere with clicks
        canvas.classList.add('captcha-noise');
        
        const ctx = canvas.getContext('2d');
        
        // Draw random lines
        for (let i = 0; i < 8; i++) {
            ctx.beginPath();
            ctx.moveTo(Math.random() * canvas.width, Math.random() * canvas.height);
            ctx.lineTo(Math.random() * canvas.width, Math.random() * canvas.height);
            ctx.strokeStyle = getRandomColor(0.3);
            ctx.lineWidth = Math.random() * 2;
            ctx.stroke();
        }
        
        // Draw random dots
        for (let i = 0; i < 50; i++) {
            ctx.beginPath();
            const x = Math.random() * canvas.width;
            const y = Math.random() * canvas.height;
            const radius = Math.random() * 2;
            ctx.arc(x, y, radius, 0, Math.PI * 2);
            ctx.fillStyle = getRandomColor(0.5);
            ctx.fill();
        }
        
        container.appendChild(canvas);
    }
    
    // Remove visual noise from captcha
    function clearNoise(container) {
        const noiseCanvas = container.querySelector('.captcha-noise');
        if (noiseCanvas) {
            container.removeChild(noiseCanvas);
        }
    }
    
    // Helper function to generate random colors
    function getRandomColor(alpha) {
        const r = Math.floor(Math.random() * 256);
        const g = Math.floor(Math.random() * 256);
        const b = Math.floor(Math.random() * 256);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
});
