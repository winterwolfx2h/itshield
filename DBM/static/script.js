document.addEventListener('DOMContentLoaded', () => {
    const socket = io({
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000
    });
    const dataList = document.getElementById('data-list');
    const dbTypeSelect = document.getElementById('dbTypeSelect');
    let lastDbType = dbTypeSelect.value;

    function updateTable(data, dbType) {
        console.log(`Updating table for ${dbType} with ${data.length} entries`);
        dataList.innerHTML = ''; // Clear table to prevent stale data
        const newRows = document.createDocumentFragment();
        data.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${item[0]}</td>
                <td>${item[1]}</td>
                <td>${item[2]}</td>
                <td>${item[3]}</td>
                <td>${item[4]}</td>
                <td>${item[5]}</td>
                <td>${item[6]}</td>
                <td>${item[7]}</td>
                <td>${item[8]}</td>
                <td>${item[9].replace(/\n/g, "<br>")}</td>
            `;
            newRows.appendChild(row);
        });
        dataList.appendChild(newRows);
    }

    socket.on('realtime_data_mysql', function(data) {
        console.log(`Received realtime_data_mysql, current dbType: ${dbTypeSelect.value}`);
        if (dbTypeSelect.value === 'mysql') {
            updateTable(data, 'mysql');
        }
    });

    socket.on('realtime_data_postgres', function(data) {
        console.log(`Received realtime_data_postgres, current dbType: ${dbTypeSelect.value}`);
        if (dbTypeSelect.value === 'postgres') {
            updateTable(data, 'postgres');
        }
    });

    // Debounce dropdown change to prevent rapid emissions
    let debounceTimeout;
    dbTypeSelect.addEventListener('change', () => {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => {
            lastDbType = dbTypeSelect.value;
            console.log(`Dropdown changed to ${lastDbType}, requesting data`);
            dataList.innerHTML = ''; // Clear table on change
            socket.emit('request_data', lastDbType);
        }, 300);
    });

    socket.on('connect', () => {
        console.log('Socket connected:', socket.id);
        socket.emit('request_data', lastDbType);
    });

    socket.on('disconnect', () => {
        console.log('Socket disconnected');
    });

    socket.on('connect_error', (error) => {
        console.error('Socket connection error:', error);
    });

    // Handle server response to request_data
    socket.on('initial_data', (data) => {
        console.log(`Received initial_data for ${data.dbType}`);
        if (data.dbType === dbTypeSelect.value) {
            updateTable(data.data, data.dbType);
        }
    });
});