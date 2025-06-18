// Scheduler SPA JS
const DAYS = ['M', 'T', 'W', 'R', 'F', 'S', 'U'];
const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const HOURS = [
    '08', '09', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21'
];
const HOUR_LABELS = [
    '8am', '9am', '10am', '11am', '12pm', '1pm', '2pm', '3pm', '4pm', '5pm', '6pm', '7pm', '8pm', '9pm'
];

let selected = new Set();
let info = {};
let isReadOnly = false;
let scheduleId = '';
let userId = '';

function dayhourKey(day, hour) {
    return day + hour;
}

function getCellColor(dayhour) {
    if (!info.dayhours || !info.count) return 'bg-white';
    const count = info.dayhours[dayhour] || 0;
    if (count === 0) return 'bg-white';
    // Build sorted unique list of counts
    const counts = Object.values(info.dayhours).filter(x => x > 0);
    const uniqueSorted = Array.from(new Set(counts)).sort((a, b) => b - a);
    if (uniqueSorted.length === 0) return 'bg-white';
    if (count === info.count) return 'bg-100'; // 100% of users
    if (count === uniqueSorted[0]) return 'bg-1st'; // 1st most common (not 100%)
    if (uniqueSorted[1] !== undefined && count === uniqueSorted[1]) return 'bg-2nd';
    if (uniqueSorted[2] !== undefined && count === uniqueSorted[2]) return 'bg-3rd';
    if (info.count && count / info.count < 0.7) return 'bg-red';
    return 'bg-white';
}

function renderGrid() {
    const grid = document.getElementById('schedule-grid');
    grid.innerHTML = '';
    // Top-left empty
    grid.appendChild(cell('schedule-header', ''));
    // Day headers
    for (let d = 0; d < DAYS.length; d++) {
        const headerDiv = document.createElement('div');
        headerDiv.className = 'schedule-header';
        headerDiv.style.display = 'flex';
        headerDiv.style.flexDirection = 'column';
        headerDiv.style.alignItems = 'center';
        headerDiv.style.justifyContent = 'center';
        // Day name
        const dayLabel = document.createElement('div');
        dayLabel.textContent = DAY_LABELS[d];
        headerDiv.appendChild(dayLabel);
        grid.appendChild(headerDiv);
    }
    // Time rows
    for (let h = 0; h < HOURS.length; h++) {
        // Hour label
        const hour = HOURS[h];
        grid.appendChild(cell('hour-label', HOUR_LABELS[h]));
        // Day cells
        for (let d = 0; d < DAYS.length; d++) {
            const day = DAYS[d];
            const key = dayhourKey(day, hour);
            const dayhourCell = document.createElement('div');
            dayhourCell.className = 'schedule-cell';
            dayhourCell.dataset.key = key;
            dayhourCell.dataset.count = info.dayhours ? (info.dayhours[key] || 0) : 0;
            dayhourCell.classList.add(getCellColor(key));
            if (selected.has(key)) {
                dayhourCell.classList.add('selected');
            }
            // Show count if any selections
            if (info.dayhours && info.dayhours[key]) {
                const countSpan = document.createElement('span');
                countSpan.className = 'cell-count';
                countSpan.textContent = info.dayhours[key];
                dayhourCell.appendChild(countSpan);
            }
            // Make cells clickable unless read-only
            if (!isReadOnly) {
                dayhourCell.addEventListener('click', function() {
                    toggleCell(this);
                });
            }
            grid.appendChild(dayhourCell);
        }
    }
}

function cell(className, text) {
    const div = document.createElement('div');
    div.className = className;
    div.textContent = text;
    return div;
}

function toggleCell(cell) {
    const key = cell.dataset.key;
    if (selected.has(key)) {
        selected.delete(key);
        cell.classList.remove('selected');
    } else {
        selected.add(key);
        cell.classList.add('selected');
    }
    // Show save button as dirty
    const saveBtn = document.getElementById('save-btn');
    if (saveBtn) {
        saveBtn.classList.add('btn-warning');
        saveBtn.classList.remove('btn-success');
        saveBtn.classList.remove('btn-primary');
        document.getElementById('save-status').textContent = 'Unsaved changes';
    }
}

function fetchScheduleInfo() {
    // Make sure we're using the window.scheduleId if available
    const currentScheduleId = window.scheduleId || scheduleId;
    
    console.log(`Fetching schedule info for scheduleId: ${currentScheduleId}`);
    
    // Check if scheduleId is missing
    if (!currentScheduleId) {
        console.error("Missing scheduleId - cannot fetch schedule info");
        const grid = document.getElementById('schedule-grid');
        if (grid) {
            grid.innerHTML = `<div class="alert alert-danger">
                <strong>Error: Missing schedule ID</strong>
                <p>The schedule ID was not found. Please try refreshing the page or returning to the home page.</p>
                <p><a href="/" class="btn btn-primary mt-3">Return to Home</a></p>
            </div>`;
        }
        return;
    }
    
    // Create a new AbortController to allow cancelling the fetch request
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
    
    fetch(`/s/${currentScheduleId}/info`, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        signal: controller.signal
    })
    .then(response => {
        clearTimeout(timeoutId);
        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);
        
        // Check content type
        const contentType = response.headers.get('content-type');
        console.log('Content-Type:', contentType);
        
        if (!contentType || !contentType.includes('application/json')) {
            // If not JSON, read as text to see what we got
            return response.text().then(text => {
                console.log('Non-JSON response:', text.substring(0, 200) + '...');
                throw new Error(`Server returned a non-JSON response from /s/${scheduleId}/info`);
            });
        }
        
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || `Server error: ${response.status}`);
            });
        }
        
        return response.json();
    })
    .then(data => {
        console.log('Received data:', data);
        if (data.error) {
            throw new Error(data.error);
        }
        info = data;
        renderGrid();
        setupSaveButton();
    })
    .catch(error => {
        
        console.error('Error fetching schedule info:', error);
        // Display user-friendly error message on the page
        const grid = document.getElementById('schedule-grid');
        if (grid) {
            grid.innerHTML = `<div class="alert alert-danger">
                <strong>Error loading schedule information</strong>
                <p>Please check that the schedule exists and try refreshing the page.</p>
                <p><small>Technical details: ${error.message}</small></p>
                <p><a href="/" class="btn btn-primary mt-3">Return to Home</a></p>
            </div>`;
        }
    });
}

function setupSaveButton() {
    const saveBtn = document.getElementById('save-btn');
    if (!saveBtn || isReadOnly) return;
    
    saveBtn.addEventListener('click', function() {
        // Call the API to save selections
        saveSelections();
    });
}

function saveSelections() {
    const saveBtn = document.getElementById('save-btn');
    const saveStatus = document.getElementById('save-status');
    
    // Make sure we're using window variables if available
    const currentScheduleId = window.scheduleId || scheduleId;
    const currentUserId = window.userId || userId;
    
    if (!currentScheduleId || !currentUserId) {
        console.error("Missing scheduleId or userId - cannot save selections");
        saveStatus.textContent = 'Error: Missing schedule or user ID';
        return;
    }
    
    saveBtn.disabled = true;
    saveStatus.textContent = 'Saving...';
    
    fetch(`/u/${currentScheduleId}/${currentUserId}/selections`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(Array.from(selected))
    })
    .then(response => {
        if (response.status === 403) {
            // Name required
            window.location.href = '/set_name?next=' + encodeURIComponent(window.location.pathname);
            return null;
        }
        return response.json();
    })
    .then(data => {
        if (!data) return; // Redirect happened
        
        saveBtn.disabled = false;
        saveBtn.classList.remove('btn-warning');
        saveBtn.classList.add('btn-success');
        saveStatus.textContent = 'Saved!';
        
        // Refresh the info after saving
        fetchScheduleInfo();
        
        // Reset to primary button after 2 seconds
        setTimeout(() => {
            saveBtn.classList.remove('btn-success');
            saveBtn.classList.add('btn-primary');
            saveStatus.textContent = '';
        }, 2000);
    })
    .catch(error => {
        console.error('Error saving selections:', error);
        saveBtn.disabled = false;
        saveStatus.textContent = 'Error saving: ' + error.message;
    });
}

function loadUserSelections() {
    // Make sure we're using window variables if available
    const currentScheduleId = window.scheduleId || scheduleId;
    const currentUserId = window.userId || userId;
    
    if (!currentScheduleId || !currentUserId) {
        console.error("Missing scheduleId or userId - cannot load selections");
        const grid = document.getElementById('schedule-grid');
        if (grid) {
            grid.innerHTML = `<div class="alert alert-danger">
                <strong>Error: Missing schedule or user ID</strong>
                <p>The necessary IDs were not found. Please try refreshing the page or returning to the home page.</p>
                <p><a href="/" class="btn btn-primary mt-3">Return to Home</a></p>
            </div>`;
        }
        return;
    }
    
    console.log(`Loading selections for schedule: ${currentScheduleId}, user: ${currentUserId}`);
    
    fetch(`/u/${currentScheduleId}/${currentUserId}/selections`, {
        headers: {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        selected = new Set(data);
        fetchScheduleInfo();
    })
    .catch(error => console.error('Error loading selections:', error));
}

// Schedule initialization will be done in the individual pages' script sections
