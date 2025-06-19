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
let blackouts = new Set();
let info = {};
let isReadOnly = false;
let isOwner = window.isOwner || false; // Default to false if not set
let scheduleId = '';
let userId = '';

function dayhourKey(day, hour) {
    return day + hour;
}

function getCellColor(dayhour) {
    // Check if this is a blackout cell
    if (blackouts.has(dayhour)) {
        return 'bg-blackout';
    }
    
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
    if (!grid) return; // Exit if grid doesn't exist (e.g., on schedule page)
    
    grid.innerHTML = '';
    
    // Top-left empty
    grid.appendChild(cell('schedule-header', ''));
    
    // Day headers
    for (let d = 0; d < DAYS.length; d++) {
        const headerDiv = document.createElement('div');
        headerDiv.className = 'schedule-header day-header';
        headerDiv.style.display = 'flex';
        headerDiv.style.flexDirection = 'column';
        headerDiv.style.alignItems = 'center';
        headerDiv.style.justifyContent = 'center';
        headerDiv.dataset.day = DAYS[d];
        
        // Day name
        const dayLabel = document.createElement('div');
        dayLabel.textContent = DAY_LABELS[d];
        headerDiv.appendChild(dayLabel);
        
        // Copy button (only show if not read-only)
        if (!isReadOnly && d < DAYS.length - 1) { // Don't show copy button on last column
            const copyBtn = document.createElement('button');
            copyBtn.className = 'btn btn-sm btn-outline-secondary mt-1';
            copyBtn.textContent = 'copy →';
            copyBtn.onclick = function(e) {
                e.stopPropagation();
                copyColumn(d);
            };
            headerDiv.appendChild(copyBtn);
        }
        
        // Make day header clickable (unless read-only)
        if (!isReadOnly) {
            headerDiv.style.cursor = 'pointer';
            headerDiv.addEventListener('click', function() {
                toggleColumn(d);
            });
        }
        
        grid.appendChild(headerDiv);
    }
    
    // Time rows
    for (let h = 0; h < HOURS.length; h++) {
        // Hour label
        const hour = HOURS[h];
        const hourLabel = cell('hour-label', HOUR_LABELS[h]);
        hourLabel.dataset.hour = hour;
        
        // Make hour label clickable (unless read-only)
        if (!isReadOnly) {
            hourLabel.style.cursor = 'pointer';
            hourLabel.addEventListener('click', function() {
                toggleRow(h);
            });
        }
        
        grid.appendChild(hourLabel);
        
        // Day cells
        for (let d = 0; d < DAYS.length; d++) {
            const day = DAYS[d];
            const key = dayhourKey(day, hour);
            const dayhourCell = document.createElement('div');
            dayhourCell.className = 'schedule-cell';
            dayhourCell.dataset.key = key;
            dayhourCell.dataset.day = day;
            dayhourCell.dataset.hour = hour;
            dayhourCell.dataset.count = info.dayhours ? (info.dayhours[key] || 0) : 0;
            dayhourCell.classList.add(getCellColor(key));
            
            if (selected.has(key)) {
                dayhourCell.classList.add('selected');
            }
            
            if (blackouts.has(key)) {
                dayhourCell.classList.add('blackout');
            }
            
            // Add star icon for 100% selection
            if (info.dayhours && info.count && info.dayhours[key] === info.count && info.count > 0) {
                const starSpan = document.createElement('span');
                starSpan.className = 'star-icon';
                starSpan.textContent = '★';
                dayhourCell.appendChild(starSpan);
            }
            
            // Show count if any selections
            if (info.dayhours && info.dayhours[key]) {
                const countSpan = document.createElement('span');
                countSpan.className = 'cell-count';
                countSpan.textContent = info.dayhours[key];
                dayhourCell.appendChild(countSpan);
            }
            
            // Make cells clickable based on context
            if (!isReadOnly) {
                dayhourCell.addEventListener('click', function() {
                    console.log('Cell clicked:', key, 'isOwner:', window.isOwner, 'pathname:', window.location.pathname);
                    // On schedule page with owner permissions, handle blackout clicks
                    if (window.location.pathname.includes('/s/') && isOwner) {
                        console.log('Calling toggleBlackout');
                        toggleBlackout(this);
                    } else {
                        // Only allow regular cell selection if not a blackout cell
                        if (!blackouts.has(key)) {
                            console.log('Calling toggleCell');
                            toggleCell(this);
                        }
                    }
                });
            } else if (window.location.pathname.includes('/s/') && isOwner) {
                // For owners on schedule page, even if marked read-only, allow blackout clicks
                dayhourCell.addEventListener('click', function() {
                    console.log('Read-only owner cell clicked, calling toggleBlackout');
                    toggleBlackout(this);
                });
            }
            
            grid.appendChild(dayhourCell);
        }
    }
    
    // Instructions are now in the template, controlled by Jinja variables
}

function toggleRow(hourIndex) {
    const hour = HOURS[hourIndex];
    const rowCells = [];
    
    // Get all cells in this row
    for (let d = 0; d < DAYS.length; d++) {
        const key = dayhourKey(DAYS[d], hour);
        rowCells.push(key);
    }
    
    // On schedule page with owner permissions, toggle blackouts instead of selections
    if (window.location.pathname.includes('/s/') && isOwner) {
        // Check if any cells in row are blackouts
        const anyBlackout = rowCells.some(key => blackouts.has(key));
        
        // If any are blackouts, turn them all off. Otherwise, turn them all on.
        rowCells.forEach(key => {
            const cell = document.querySelector(`[data-key="${key}"]`);
            
            if (anyBlackout) {
                // Remove blackout
                if (blackouts.has(key)) {
                    blackouts.delete(key);
                    cell.classList.remove('blackout', 'bg-blackout');
                    // Restore original color based on popularity
                    const colorClass = getCellColor(key);
                    cell.classList.add(colorClass);
                }
            } else {
                // Add blackout
                blackouts.add(key);
                // Remove any selection if this cell was selected
                selected.delete(key);
                cell.classList.remove('selected');
                // Remove all color classes and apply blackout styling
                cell.classList.remove('bg-white', 'bg-100', 'bg-1st', 'bg-2nd', 'bg-3rd', 'bg-red');
                cell.classList.add('blackout', 'bg-blackout');
            }
        });
        
        markBlackoutDirty();
    } else {
        // Check if any cells in row are selected
        const anySelected = rowCells.some(key => selected.has(key));
        
        // If any are selected, turn them all off. Otherwise, turn them all on.
        rowCells.forEach(key => {
            const cell = document.querySelector(`[data-key="${key}"]`);
            // Skip blackout cells
            if (blackouts.has(key)) return;
            
            if (anySelected) {
                selected.delete(key);
                cell.classList.remove('selected');
            } else {
                selected.add(key);
                cell.classList.add('selected');
            }
        });
        
        markDirty();
    }
}

function toggleColumn(dayIndex) {
    const day = DAYS[dayIndex];
    const columnCells = [];
    
    // Get all cells in this column
    for (let h = 0; h < HOURS.length; h++) {
        const key = dayhourKey(day, HOURS[h]);
        columnCells.push(key);
    }
    
    // On schedule page with owner permissions, toggle blackouts instead of selections
    if (window.location.pathname.includes('/s/') && isOwner) {
        // Check if any cells in column are blackouts
        const anyBlackout = columnCells.some(key => blackouts.has(key));
        
        // If any are blackouts, turn them all off. Otherwise, turn them all on.
        columnCells.forEach(key => {
            const cell = document.querySelector(`[data-key="${key}"]`);
            
            if (anyBlackout) {
                // Remove blackout
                if (blackouts.has(key)) {
                    blackouts.delete(key);
                    cell.classList.remove('blackout', 'bg-blackout');
                    // Restore original color based on popularity
                    const colorClass = getCellColor(key);
                    cell.classList.add(colorClass);
                }
            } else {
                // Add blackout
                blackouts.add(key);
                // Remove any selection if this cell was selected
                selected.delete(key);
                cell.classList.remove('selected');
                // Remove all color classes and apply blackout styling
                cell.classList.remove('bg-white', 'bg-100', 'bg-1st', 'bg-2nd', 'bg-3rd', 'bg-red');
                cell.classList.add('blackout', 'bg-blackout');
            }
        });
        
        markBlackoutDirty();
    } else {
        // Check if any cells in column are selected
        const anySelected = columnCells.some(key => selected.has(key));
        
        // If any are selected, turn them all off. Otherwise, turn them all on.
        columnCells.forEach(key => {
            const cell = document.querySelector(`[data-key="${key}"]`);
            // Skip blackout cells
            if (blackouts.has(key)) return;
            
            if (anySelected) {
                selected.delete(key);
                cell.classList.remove('selected');
            } else {
                selected.add(key);
                cell.classList.add('selected');
            }
        });
        
        markDirty();
    }
}

function copyColumn(fromDayIndex) {
    if (fromDayIndex >= DAYS.length - 1) return; // Can't copy from last column
    
    const fromDay = DAYS[fromDayIndex];
    const toDay = DAYS[fromDayIndex + 1];
    
    // On schedule page with owner permissions, copy blackouts instead of selections
    if (window.location.pathname.includes('/s/') && isOwner) {
        // Get blackouts from source column
        const fromBlackouts = [];
        for (let h = 0; h < HOURS.length; h++) {
            const key = dayhourKey(fromDay, HOURS[h]);
            if (blackouts.has(key)) {
                fromBlackouts.push(HOURS[h]);
            }
        }
        
        // Clear target column blackouts
        for (let h = 0; h < HOURS.length; h++) {
            const key = dayhourKey(toDay, HOURS[h]);
            if (blackouts.has(key)) {
                blackouts.delete(key);
                const cell = document.querySelector(`[data-key="${key}"]`);
                cell.classList.remove('blackout', 'bg-blackout');
                // Restore original color based on popularity
                const colorClass = getCellColor(key);
                cell.classList.add(colorClass);
            }
        }
        
        // Copy blackouts to target column
        fromBlackouts.forEach(hour => {
            const key = dayhourKey(toDay, hour);
            blackouts.add(key);
            // Remove any selection if this cell was selected
            selected.delete(key);
            const cell = document.querySelector(`[data-key="${key}"]`);
            cell.classList.remove('selected');
            // Remove all color classes and apply blackout styling
            cell.classList.remove('bg-white', 'bg-100', 'bg-1st', 'bg-2nd', 'bg-3rd', 'bg-red');
            cell.classList.add('blackout', 'bg-blackout');
        });
        
        markBlackoutDirty();
    } else {
        // Get selections from source column
        const fromSelections = [];
        for (let h = 0; h < HOURS.length; h++) {
            const key = dayhourKey(fromDay, HOURS[h]);
            if (selected.has(key)) {
                fromSelections.push(HOURS[h]);
            }
        }
        
        // Clear target column
        for (let h = 0; h < HOURS.length; h++) {
            const key = dayhourKey(toDay, HOURS[h]);
            selected.delete(key);
            const cell = document.querySelector(`[data-key="${key}"]`);
            cell.classList.remove('selected');
        }
        
        // Copy selections to target column
        fromSelections.forEach(hour => {
            const key = dayhourKey(toDay, hour);
            // Skip blackout cells
            if (blackouts.has(key)) return;
            
            selected.add(key);
            const cell = document.querySelector(`[data-key="${key}"]`);
            cell.classList.add('selected');
        });
        
        markDirty();
    }
}

function markDirty() {
    // Show save button as dirty
    const saveBtn = document.getElementById('save-btn');
    if (saveBtn) {
        saveBtn.classList.add('btn-warning');
        saveBtn.classList.remove('btn-success');
        saveBtn.classList.remove('btn-primary');
        document.getElementById('save-status').textContent = 'Unsaved changes';
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
    console.log('toggleCell called for key:', key);
    if (selected.has(key)) {
        selected.delete(key);
        cell.classList.remove('selected');
    } else {
        selected.add(key);
        cell.classList.add('selected');
    }
    markDirty();
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
        
        // Set owner status from response
        isOwner = data.is_owner || false;

        // Load blackouts from the response
        if (data.blackouts) {
            blackouts = new Set(data.blackouts);
        }
        
        renderGrid();
        renderSummaryGrid(); // Also render summary grid if it exists
        setupSaveButton();
        setupNameInput();
        if (typeof setupBlackoutSaveButton === 'function') {
            setupBlackoutSaveButton();
        }
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

function setupBlackoutSaveButton() {
    const saveBtn = document.getElementById('save-blackout-btn');
    if (!saveBtn) return;
    
    saveBtn.addEventListener('click', function() {
        saveBlackouts();
    });
}

function saveSelections() {
    const saveBtn = document.getElementById('save-btn');
    const saveStatus = document.getElementById('save-status');
    const nameInput = document.getElementById('user-name');
    const nameError = document.getElementById('name-error');
    
    // Validate name input
    if (nameInput && (!nameInput.value || nameInput.value.trim() === '')) {
        if (nameError) {
            nameError.classList.remove('d-none');
        }
        nameInput.focus();
        return;
    }
    
    // Hide name error if it was showing
    if (nameError) {
        nameError.classList.add('d-none');
    }
    
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
    
    // First, update the name in session if it has changed
    const userName = nameInput ? 
        nameInput.value.trim() : 
        null;
    const savePromise = userName ? 
        fetch('/set_name', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: 'name=' + encodeURIComponent(userName)
        }).then(response => {
            if (!response.ok) {
                throw new Error('Failed to save name');
            }
            return response;
        }) : 
        Promise.resolve();
    
    savePromise.then(() => {
        return fetch(`/u/${currentScheduleId}/${currentUserId}/selections`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(Array.from(selected))
        });
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

function setupNameInput() {
    const nameInput = document.getElementById('user-name');
    const nameError = document.getElementById('name-error');
    
    if (nameInput && nameError) {
        nameInput.addEventListener('input', function() {
            if (nameInput.value.trim() !== '') {
                nameError.classList.add('d-none');
            }
        });
    }
}

function renderSummaryGrid() {
    const grid = document.getElementById('summary-schedule-grid');
    if (!grid) return;
    
    grid.innerHTML = '';
    
    // Top-left empty
    const emptyHeader = document.createElement('div');
    emptyHeader.className = 'summary-schedule-header';
    grid.appendChild(emptyHeader);
    
    // Day headers
    for (let d = 0; d < DAYS.length; d++) {
        const headerDiv = document.createElement('div');
        headerDiv.className = 'summary-schedule-header';
        headerDiv.textContent = DAY_LABELS[d];
        grid.appendChild(headerDiv);
    }
    
    // Time rows
    for (let h = 0; h < HOURS.length; h++) {
        // Hour label
        const hour = HOURS[h];
        const hourLabel = document.createElement('div');
        hourLabel.className = 'summary-hour-label';
        hourLabel.textContent = HOUR_LABELS[h];
        grid.appendChild(hourLabel);
        
        // Day cells
        for (let d = 0; d < DAYS.length; d++) {
            const day = DAYS[d];
            const key = dayhourKey(day, hour);
            
            const dayhourCell = document.createElement('div');
            dayhourCell.className = 'summary-schedule-cell';
            dayhourCell.dataset.key = key;
            
            // Set background color based on selection count
            const colorClass = getCellColor(key);
            dayhourCell.classList.add(colorClass);
            
            // Show blackout cells differently in summary
            if (blackouts.has(key)) {
                dayhourCell.textContent = '✕';
                dayhourCell.style.color = '#fff';
            } else {
                // Show count if any selections
                if (info.dayhours && info.dayhours[key]) {
                    dayhourCell.textContent = info.dayhours[key];
                }
                
                // Add star icon for 100% selection
                if (info.dayhours && info.count && info.dayhours[key] === info.count && info.count > 0) {
                    const starSpan = document.createElement('span');
                    starSpan.className = 'summary-star-icon';
                    starSpan.textContent = '★';
                    dayhourCell.appendChild(starSpan);
                }
            }
            
            grid.appendChild(dayhourCell);
        }
    }
}

function toggleBlackout(cell) {
    const key = cell.dataset.key;
    
    console.log('toggleBlackout called for key:', key);
    console.log('Current blackouts:', Array.from(blackouts));
    
    if (blackouts.has(key)) {
        // Remove blackout
        blackouts.delete(key);
        cell.classList.remove('blackout');
        cell.classList.remove('bg-blackout');
        // Restore original color based on popularity
        const colorClass = getCellColor(key);
        cell.classList.add(colorClass);
        console.log('Removed blackout, added color class:', colorClass);
    } else {
        // Add blackout
        blackouts.add(key);
        // Remove any selection if this cell was selected
        selected.delete(key);
        cell.classList.remove('selected');
        // Remove all color classes and apply blackout styling
        cell.classList.remove('bg-white', 'bg-100', 'bg-1st', 'bg-2nd', 'bg-3rd', 'bg-red');
        cell.classList.add('blackout');
        cell.classList.add('bg-blackout');
        console.log('Added blackout for key:', key);
    }
    markBlackoutDirty();
}

function markBlackoutDirty() {
    // Show save button as dirty for blackouts
    const saveBtn = document.getElementById('save-blackout-btn');
    if (saveBtn) {
        saveBtn.classList.add('btn-warning');
        saveBtn.classList.remove('btn-success');
        saveBtn.classList.remove('btn-primary');
        const saveStatus = document.getElementById('save-blackout-status');
        if (saveStatus) {
            saveStatus.textContent = 'Unsaved blackout changes';
        }
    }
}

function saveBlackouts() {
    const saveBtn = document.getElementById('save-blackout-btn');
    const saveStatus = document.getElementById('save-blackout-status');
    
    const currentScheduleId = window.scheduleId || scheduleId;
    const schedulePassword = window.schedulePassword || '';
    
    if (!currentScheduleId) {
        console.error("Missing scheduleId - cannot save blackouts");
        saveStatus.textContent = 'Error: Missing schedule ID';
        return;
    }
    
    saveBtn.disabled = true;
    saveStatus.textContent = 'Saving blackouts...';
    
    const data = {
        blackouts: Array.from(blackouts),
        pw: schedulePassword
    };
    
    fetch(`/s/${currentScheduleId}/blackouts`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(Array.from(blackouts))
    })
    .then(response => response.json())
    .then(data => {
        saveBtn.disabled = false;
        if (data.error) {
            saveStatus.textContent = 'Error: ' + data.error;
        } else {
            saveBtn.classList.remove('btn-warning');
            saveBtn.classList.add('btn-success');
            saveStatus.textContent = 'Blackouts saved!';
            
            // Refresh the info after saving
            fetchScheduleInfo();
            
            // Reset to primary button after 2 seconds
            setTimeout(() => {
                saveBtn.classList.remove('btn-success');
                saveBtn.classList.add('btn-primary');
                saveStatus.textContent = '';
            }, 2000);
        }
    })
    .catch(error => {
        console.error('Error saving blackouts:', error);
        saveBtn.disabled = false;
        saveStatus.textContent = 'Error saving blackouts: ' + error.message;
    });
}

function loadBlackouts() {
    const currentScheduleId = window.scheduleId || scheduleId;
    
    if (!currentScheduleId) {
        console.error("Missing scheduleId - cannot load blackouts");
        return;
    }
    
    fetch(`/s/${currentScheduleId}/blackouts`, {
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
        blackouts = new Set(data);
        renderGrid();
        renderSummaryGrid();
    })
    .catch(error => console.error('Error loading blackouts:', error));
}

// Schedule initialization will be done in the individual pages' script sections
