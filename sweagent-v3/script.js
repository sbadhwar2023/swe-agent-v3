async function performSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    const query = searchInput.value.trim();

    if (!query) return;

    searchResults.innerHTML = 'Searching...';

    try {
        const response = await fetch(`https://en.wikipedia.org/w/api.php?action=opensearch&search=${encodeURIComponent(query)}&format=json&origin=*`);
        const data = await response.json();

        // Clear previous results
        searchResults.innerHTML = '';

        // Process results
        if (data && data[1].length > 0) {
            for (let i = 0; i < data[1].length; i++) {
                const resultItem = document.createElement('div');
                resultItem.className = 'result-item';
                resultItem.innerHTML = `
                    <h3><a href="${data[3][i]}" target="_blank">${data[1][i]}</a></h3>
                    <p>${data[2][i] || 'No description available'}</p>
                `;
                searchResults.appendChild(resultItem);
            }
        } else {
            searchResults.innerHTML = '<p>No results found</p>';
        }
    } catch (error) {
        searchResults.innerHTML = '<p>Error performing search. Please try again.</p>';
        console.error('Search error:', error);
    }
}

// Add event listener for Enter key
document.getElementById('searchInput').addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        performSearch();
    }
});