document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generate-btn');
    const gameSelect = document.getElementById('game-select');
    const resultContainer = document.getElementById('result-container');

    generateBtn.addEventListener('click', () => {
        const maxNumber = parseInt(gameSelect.value);
        const combination = generateCombination(maxNumber);
        
        // Clear previous results
        resultContainer.innerHTML = '';
        
        // Create and append balls with animation delay
        combination.forEach((num, index) => {
            const ball = document.createElement('span');
            ball.classList.add('ball');
            // Format number to always be two digits (e.g., '07', '42')
            ball.textContent = num.toString().padStart(2, '0');
            
            // Add a simple fade-in effect via CSS if desired, 
            // but keeping it simple here for immediate feedback
            resultContainer.appendChild(ball);
        });
        
        resultContainer.classList.remove('hidden');
    });

    function generateCombination(max) {
        const numbers = new Set();
        
        // Keep generating random numbers until we have 6 unique ones
        while (numbers.size < 6) {
            const randomNum = Math.floor(Math.random() * max) + 1;
            numbers.add(randomNum);
        }
        
        // Convert Set to Array and sort ascending
        return Array.from(numbers).sort((a, b) => a - b);
    }
});