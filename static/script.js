document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchForm');
    const searchBtn = document.getElementById('searchBtn');
    
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            if (searchBtn) {
                searchBtn.innerHTML = 'Searching...';
                searchBtn.disabled = true;
            }
        });
    }
});
