document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const dataList = document.getElementById('data-list');
    const dbTypeSelect = document.getElementById('dbTypeSelect');

    function updateTable(data) {
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
        dataList.innerHTML = '';
        dataList.appendChild(newRows);
    }

    socket.on('realtime_data_mysql', function(data) {
        if (dbTypeSelect.value === 'mysql') {
            updateTable(data);
        }
    });

    socket.on('realtime_data_postgres', function(data) {
        if (dbTypeSelect.value === 'postgres') {
            updateTable(data);
        }
    });

    dbTypeSelect.addEventListener('change', () => {
        dataList.innerHTML = '';
        socket.emit('request_data', dbTypeSelect.value);
    });

    socket.on('connect', () => {
        socket.emit('request_data', dbTypeSelect.value);
    });
});