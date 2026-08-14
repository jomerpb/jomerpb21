document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generate-btn');
    const gameSelect = document.getElementById('game-select');
    const resultContainer = document.getElementById('result-container');

    generateBtn.addEventListener('click', () => {
        const maxNumber = parseInt(gameSelect.value);
        const combination = generateCombination(maxNumber);
        
        resultContainer.innerHTML = '';
        
        combination.forEach((num, index) => {
            const ball = document.createElement('span');
            ball.classList.add('ball');
            ball.textContent = num.toString().padStart(2, '0');
            resultContainer.appendChild(ball);
        });
        
        resultContainer.classList.remove('hidden');
    });

    function generateCombination(max) {
        const numbers = new Set();
        while (numbers.size < 6) {
            const randomNum = Math.floor(Math.random() * max) + 1;
            numbers.add(randomNum);
        }
        return Array.from(numbers).sort((a, b) => a - b);
    }
});