// Scheduler SPA JS
const DAYS = ['M', 'T', 'W', 'R', 'F', 'S', 'U'];
const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const HOURS = [
    '08', '09', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21'
];
const HOUR_LABELS = [
    '8am', '9am', '10am', '11am', '12pm', '1pm', '2pm', '3pm', '4pm', '5pm', '6pm', '7pm', '8pm', '9pm'
];

const team = window.location.pathname.split('/')[1];
let selected = new Set();
let info = {};

function dayhourKey(day, hour) {
    return day + hour;
}

function getCellColor(dayhour) {
    if (!info.dayhours || !info.count) return '';
    const count = info.dayhours[dayhour] || 0;
    if (count === 0) return 'bg-white';
    // Build sorted unique list of counts
    const counts = Object.values(info.dayhours).filter(x => x > 0);
    const uniqueSorted = Array.from(new Set(counts)).sort((a, b) => b - a);
    if (uniqueSorted.length === 0) return 'bg-white';
    if (count === uniqueSorted[0]) {
        if (count === info.count) return 'bg-100'; // 100% of users
        return 'bg-1st'; // 1st most common (not 100%)
    }
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
    // Day headers + copy buttons
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
        dayLabel.style.cursor = 'pointer';
        dayLabel.onclick = () => toggleDay(DAYS[d]);
        headerDiv.appendChild(dayLabel);
        // Copy button (except last column)
        if (d < DAYS.length - 1) {
            const copyBtn = document.createElement('button');
            copyBtn.textContent = 'copy →';
            copyBtn.className = 'copy-btn';
            copyBtn.style.fontSize = '0.8em';
            copyBtn.style.marginTop = '2px';
            copyBtn.onclick = (e) => {
                e.stopPropagation();
                copyColumn(d);
            };
            headerDiv.appendChild(copyBtn);
        } else {
            // For last column, add empty space for alignment
            const emptyDiv = document.createElement('div');
            emptyDiv.style.height = '1.7em';
            headerDiv.appendChild(emptyDiv);
        }
        grid.appendChild(headerDiv);
    }
    // Hour rows
    for (let h = 0; h < HOURS.length; h++) {
        // Start a new row
        // Hour header
        grid.appendChild(cell('schedule-hour', HOUR_LABELS[h], {
            onclick: () => toggleHour(HOURS[h])
        }));
        for (let d = 0; d < DAYS.length; d++) {
            const key = dayhourKey(DAYS[d], HOURS[h]);
            const isSelected = selected.has(key);
            const colorClass = getCellColor(key);
            let count = info.dayhours ? (info.dayhours[key] || 0) : 0;
            let inner = '';
            if (isSelected) {
                inner += '<span class="dot"></span>';
            }
            if (colorClass === 'bg-100') {
                inner += '<span class="star">★</span>';
            }
            if (count > 0) {
                inner += `<span class="count">${count}</span>`;
            }
            grid.appendChild(cellHtml(
                `schedule-cell${isSelected ? ' selected' : ''}${colorClass ? ' ' + colorClass : ''}`,
                inner,
                {
                    onclick: () => toggleCell(key)
                }
            ));
        }
    }
}

function cell(cls, text, opts = {}) {
    const el = document.createElement('div');
    el.className = cls;
    el.textContent = text;
    if (opts.onclick) el.onclick = opts.onclick;
    return el;
}

function cellHtml(cls, html, opts = {}) {
    const el = document.createElement('div');
    el.className = cls;
    el.innerHTML = html;
    if (opts.onclick) el.onclick = opts.onclick;
    return el;
}

function toggleCell(key) {
    if (selected.has(key)) selected.delete(key);
    else selected.add(key);
    renderGrid();
}

function toggleHour(hour) {
    let anySelected = false;
    for (let d = 0; d < DAYS.length; d++) {
        if (selected.has(dayhourKey(DAYS[d], hour))) anySelected = true;
    }
    for (let d = 0; d < DAYS.length; d++) {
        const key = dayhourKey(DAYS[d], hour);
        if (anySelected) selected.delete(key);
        else selected.add(key);
    }
    renderGrid();
}

function toggleDay(day) {
    let anySelected = false;
    for (let h = 0; h < HOURS.length; h++) {
        if (selected.has(dayhourKey(day, HOURS[h]))) anySelected = true;
    }
    for (let h = 0; h < HOURS.length; h++) {
        const key = dayhourKey(day, HOURS[h]);
        if (anySelected) selected.delete(key);
        else selected.add(key);
    }
    renderGrid();
}

function copyColumn(colIdx) {
    // Copy all selected cells from column colIdx to colIdx+1
    for (let h = 0; h < HOURS.length; h++) {
        const fromKey = dayhourKey(DAYS[colIdx], HOURS[h]);
        const toKey = dayhourKey(DAYS[colIdx + 1], HOURS[h]);
        if (selected.has(fromKey)) {
            selected.add(toKey);
        } else {
            selected.delete(toKey);
        }
    }
    renderGrid();
}

async function fetchSelections() {
    const resp = await fetch(`/${team}/selections`);
    if (resp.ok) {
        const data = await resp.json();
        selected = new Set(data);
    }
}

async function fetchInfo() {
    const resp = await fetch(`/${team}/info`);
    if (resp.ok) {
        info = await resp.json();
    }
}

async function saveSelections() {
    const resp = await fetch(`/${team}/selections`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(Array.from(selected))
    });
    if (resp.ok) {
        document.getElementById('save-status').textContent = 'Saved!';
        await fetchInfo();
        renderGrid();
        setTimeout(() => {
            document.getElementById('save-status').textContent = '';
        }, 1200);
    } else {
        document.getElementById('save-status').textContent = 'Error saving!';
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    await fetchSelections();
    await fetchInfo();
    renderGrid();
    document.getElementById('save-btn').onclick = saveSelections;
});
