document.addEventListener('DOMContentLoaded', () => {
    const socket = io({
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000
    });
    const dataList = document.getElementById('data-list');
    const dbTypeSelect = document.getElementById('dbTypeSelect');
    let currentDbType = dbTypeSelect.value;

    function updateTable(data, dbType) {
        if (dbType !== currentDbType) {
            console.log(`Ignoring data for ${dbType}, currentDbType is ${currentDbType}`);
            return;
        }
        console.log(`Updating table for ${dbType} with ${data.length} entries, raw data:`, data);
        dataList.innerHTML = ''; // Clear table to prevent stale data
        const newRows = document.createDocumentFragment();
        data.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${item[0] || 'N/A'}</td>
                <td>${item[1] || 'N/A'}</td>
                <td>${item[2] || 'N/A'}</td>
                <td>${item[3] || 'N/A'}</td>
                <td>${item[4] || 'N/A'}</td>
                <td>${item[5] || 'N/A'}</td>
                <td>${item[6] || 'N/A'}</td>
                <td>${item[7] || 'N/A'}</td>
                <td>${item[8] || 'N/A'}</td>
                <td>${(item[9] || '').replace(/\n/g, "<br>")}</td>
            `;
            newRows.appendChild(row);
        });
        dataList.appendChild(newRows);
    }

    socket.on('realtime_data_mysql', function(data) {
        console.log(`Received realtime_data_mysql, currentDbType: ${currentDbType}, data length: ${data.length}, raw data:`, data);
        if (currentDbType === 'mysql') {
            updateTable(data, 'mysql');
        }
    });

    socket.on('realtime_data_postgres', function(data) {
        console.log(`Received realtime_data_postgres, currentDbType: ${currentDbType}, data length: ${data.length}, raw data:`, data);
        if (currentDbType === 'postgres') {
            updateTable(data, 'postgres');
        }
    });

    // Debounce dropdown change to prevent rapid emissions
    let debounceTimeout;
    dbTypeSelect.addEventListener('change', () => {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => {
            currentDbType = dbTypeSelect.value;
            console.log(`Dropdown changed to ${currentDbType}, requesting data`);
            dataList.innerHTML = ''; // Clear table on change
            socket.emit('request_data', currentDbType);
        }, 300);
    });

    socket.on('connect', () => {
        console.log('Socket connected:', socket.id);
        socket.emit('request_data', currentDbType);
    });

    socket.on('disconnect', () => {
        console.log('Socket disconnected');
    });

    socket.on('connect_error', (error) => {
        console.error('Socket connection error:', error);
    });

    socket.on('initial_data', (data) => {
        console.log(`Received initial_data for ${data.dbType}, currentDbType: ${currentDbType}, data length: ${data.data.length}, raw data:`, data.data);
        if (data.dbType === currentDbType) {
            updateTable(data.data, data.dbType);
        }
    });
});