// Для Страницы с дешбордом
window.onload = function() {
      updateVisibleRowNumbers();
    }

// Функция для управления вкладками
function openTab(evt, tabName) {
    var i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
}

// Функция для получения логов и обновления текстовых окон
function updateLogs() {
    fetch('/logs')  // Путь к серверному обработчику
        .then(response => response.json())  // Сервер возвращает JSON (важно!)
        .then(logs => {
            document.getElementById('debug_log').value = logs.debug;
            document.getElementById('info_log').value = logs.info;
            document.getElementById('request_log').value = logs.request;
            document.getElementById('error_log').value = logs.error;
        })
        .catch(error => console.error('Ошибка при обновлении логов:', error));
}

// Обновление логов каждые 10 секунд
setInterval(updateLogs, 10000);

// Инициализация вкладки по умолчанию
document.addEventListener('DOMContentLoaded', (event) => {
    openTab(event, 'dashboard');
});

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('dashboard-btn').click();
});

document.addEventListener('DOMContentLoaded', function () {
    // юзеры для менеджера юзеров
    fetchUsers();
    // Создание выпадающего списка для шапки таблицы
    var roomHeaderCell = document.getElementById('users_table_headers').rows[0].cells[6];
    var roomSelect = document.createElement('select');
    roomSelect.classList.add('room-select');
    roomSelect.innerHTML = '<option value="">Select Room</option>';
    roomHeaderCell.innerHTML = '';
    roomHeaderCell.appendChild(roomSelect);
    
    var rooms = new Set();
    document.querySelectorAll('#users_table .room-select').forEach(function(selectElement) {
        for (var i = 0; i < selectElement.options.length; i++) {
            rooms.add(selectElement.options[i].value);
        }
    });

    rooms.forEach(function(room) {
        if (room) {
            var option = document.createElement('option');
            option.textContent = room;
            option.value = room;
            roomSelect.appendChild(option);
        }
    });

    
  roomSelect.addEventListener('change', function() {
    var selectedRoom = this.value;

    document.querySelectorAll('#users_table .room-select').forEach(function(selectElement) {
        var found = false;
        for (var i = 0; i < selectElement.options.length; i++) {
            if (selectElement.options[i].value === selectedRoom) {
                selectElement.value = selectedRoom;
                found = true;
                break;
            }
        }

        if (found) {
            var userId = selectElement.getAttribute('data-user-id');
            if (userId) {
                updateFiles(selectElement, userId);
            }
        }
    });
  });
});

function updateVisibleRowNumbers() {
      var table = document.getElementById("users_table");
      var rows = table.getElementsByTagName("tr");
      var visibleIndex = 1;
      for (var i = 0; i < rows.length; i++) {
        if (rows[i].style.display !== 'none') {
          rows[i].getElementsByTagName("TD")[0].innerHTML = visibleIndex++;
        }
      }
        var table = document.getElementById('users_table');
        var select = document.getElementById('route_filter');
        var selectedRoute = select.value;
        var displayedRow = 1;
        
          var from = dateFrom.value;
          var to = dateTo.value;                          
        
        for (var i = 0; i < table.rows.length; i++) {
          var row = table.rows[i];
          var launchDate = formatDate(row.cells[4].textContent);
          
          if (((from === '' || launchDate >= from) && (to === '' || launchDate <= to) && row.cells[3].textContent === selectedRoute) || ((from === '' || launchDate >= from) && (to === '' || launchDate <= to) && selectedRoute === '')) {
            row.style.display = ''; // Показываем строку
            table.rows[i].getElementsByTagName("TD")[0].innerHTML = displayedRow++;
          } else {
            row.style.display = 'none'; // Скрываем строку
          }
    }
    }

function updateFiles(selectElement, userId) {
    // Получаем выбранное значение room
    var room = selectElement.value || 'All Rooms';
    if (room === 'All Rooms') room = '';

    // Формируем запрос
    var url = new URL('/get-files-count', window.location.origin);
    var params = { user_id: userId, room: room === 'All Rooms' ? '' : room };
    url.search = new URLSearchParams(params).toString();

    // Выполняем запрос на сервер
    fetch(url)
    .then(function(response) {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(function(data) {
        // Обновляем количество файлов в соответствующей ячейке таблицы
        var filesCell = document.querySelector('.files-cell[data-user-id="' + userId + '"]');
        filesCell.textContent = data.total_files;

        // Обновляем last_send в соответствующей ячейке таблицы
        var lastSendCell = document.querySelector('.last-send-cell[data-user-id="' + userId + '"]');
        lastSendCell.textContent = data.last_send;
    })
    .catch(function(error) {
        console.error('Ошибка при выполнении запроса:', error);
    });
}

function updateRowNumbers() {
      var table = document.getElementById("users_table");
      var rows = table.getElementsByTagName("tr");
      for (var i = 0; i < rows.length; i++) {
        if (rows[i].style.display !== 'none') {
          rows[i].getElementsByTagName("TD")[0].innerHTML = i;
        }
      }
    }

function sortTable(n, isNumeric, isDate) {
 var table, rows, switching, i, shouldSwitch;
 table = document.getElementById("users_table");

 var headers = document.getElementById("users_table_headers").getElementsByTagName("th");
 // Удалить старые иконки сортировки
  for (let header of headers) {
    header.classList.remove("asc", "desc");
    var existingIcon = header.querySelector(".sort-icon");
    if (existingIcon) {
      header.removeChild(existingIcon);
    }
  }
 var header = headers[n];

 // Переключение направления сортировки
 var dir = header.getAttribute("data-dir") === "asc" ? "desc" : "asc"; 
 header.setAttribute("data-dir", dir); // Запомнить новое направление в атрибуте


 let tbody = table.querySelector('tbody');
 rows = Array.from(tbody.rows);

 const compareFunction = (rowA, rowB) => {
  let aValue, bValue;
  if (isNumeric) {
    aValue = parseFloat(rowA);
    bValue = parseFloat(rowB);
  } else if (isDate) {
    aValue = rowA.split('.').join('');
    bValue = rowB.split('.').join('');
  } else {
    aValue = rowB.toLowerCase();
    bValue = rowA.toLowerCase();
  }
  return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
 };

 // Отсортировать строки
 let sortedRows = [...rows].sort((rowA, rowB) => {
  const cellA = rowA.querySelector(`td:nth-child(${n + 1})`).textContent;
  const cellB = rowB.querySelector(`td:nth-child(${n + 1})`).textContent;
  return dir === "asc" ? compareFunction(cellA, cellB) : -compareFunction(cellA, cellB);
 });

 tbody.innerHTML = '';
 sortedRows.forEach(row => tbody.appendChild(row));

 // Изменение иконки сортировки
 header.classList.add(dir);
 
 var icon = document.createElement("span");
 icon.className = "sort-icon";
 if (dir === "desc") {
     icon.classList.add("desc");
 } else {
     icon.classList.add("asc");
 }
 header.appendChild(icon);

 // После сортировки обновляем номера строк
 for (i = 0; i < rows.length; i++) {
  rows[i].getElementsByTagName("TD")[0].innerHTML = i + 1; // Индексация начинается с 1
 }
 updateVisibleRowNumbers();
}


function formatDate(dateStr) {
    return dateStr.replace(/\./g, '-');
  }

document.addEventListener('DOMContentLoaded', function () {
  var dateFrom = document.getElementById('date_from');
  var dateTo = document.getElementById('date_to');

  dateFrom.onchange = dateTo.onchange = function() {
      filterTable();
  };

  function filterTable() {
      // Функция, которая фильтрует строки таблицы по выбранным датам
      var from = dateFrom.value;
      var to = dateTo.value;
      var rows = document.getElementById('users_table').getElementsByTagName('tr');
      var displayedRow = 1;

      var select = document.getElementById('route_filter');
      var selectedRoute = select.value;

      for (var i = 0; i < rows.length; i++) {
          var row = rows[i];
          var launchDate = formatDate(row.cells[4].textContent);
          if (((from === '' || launchDate >= from) && (to === '' || launchDate <= to) && row.cells[3].textContent === selectedRoute) || ((from === '' || launchDate >= from) && (to === '' || launchDate <= to) && selectedRoute === '')) {
              row.style.display = '';
              row.getElementsByTagName("TD")[0].innerHTML = displayedRow++;
          } else {
              row.style.display = 'none';
          }
      }
  }

  var table = document.getElementById('users_table');
  var select = document.getElementById('route_filter');

  select.onchange = function() {
    var selectedRoute = select.value;
    var displayedRow = 1;
    for (var i = 0; i < table.rows.length; i++) {
      var row = table.rows[i];
      if (row.cells[3].textContent === selectedRoute || selectedRoute === '') {
        row.style.display = ''; // Показываем строку
        table.rows[i].getElementsByTagName("TD")[0].innerHTML = displayedRow++;
      } else {
        row.style.display = 'none'; // Скрываем строку
      }
    }
  }

  // Инициализируем номера строк при загрузке страницы.
  updateRowNumbers();
});




// для users_manager
document.getElementById('search-user').onkeyup = function() {
    fetchUsers(this.value.toLowerCase());
};

function fetchUsers(searchValue = '') {
    fetch(`/filter_users?search=${searchValue}`)
        .then(response => response.json())
        .then(data => updateUsersTable(data));
}


function updateUsersTable(users) {
    const usersTableBody = document.querySelector('.table tbody');

    usersTableBody.innerHTML = ''; // Очищаем текущее содержимое таблицы
    users.forEach(user => {
        let buttonsHTML = ``

        // кнопка редактирования юзеров есть только у модератора и админа
        if (role > 0) {
            buttonsHTML += `
            <button onclick="openEditModal(${user.id}, '${user.username}', '${user.password}', '${user.route}')" class="btn btn-primary btn-sm">Update</button>
        `;
        }
        // кнопка удаления юзеров есть только у админа
        if (role > 1) {
            buttonsHTML += `
                <button onclick="deleteUser('${user.username}')" class="btn btn-danger btn-sm">Delete</button>
            `;
        }

        usersTableBody.innerHTML += `
            <tr>
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.password}</td>
                <td>${user.route}</td>
                <td>${buttonsHTML}</td>
            </tr>
        `;
    });
}


// Функция для открытия модального окна
function openEditModal(userId, username, password, route) {
    document.getElementById('edit-id').value = userId;
    document.getElementById('edit-username').value = username;
    document.getElementById('edit-password').value = password;
    document.getElementById('edit-route').value = route;
    document.getElementById('editModal').style.display = 'block';
}

// Функция для сохранения изменений пользователя
function saveUser() {
    const userId = document.getElementById('edit-id').value;
    const username = document.getElementById('edit-username').value;
    const password = document.getElementById('edit-password').value;
    const route = document.getElementById('edit-route').value;

    fetch(`/update_user`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `user_id=${userId}&username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}&route=${route}`
    })
    .then(response => {
        if(response.ok) {
            fetchUsers(); // Обновляем список пользователей
            closeModal(); // Закрываем модальное окно
            }
        else{
            return response.text().then(text => { throw new Error(text) });
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert(error.message); // Показываем alert с текстом ошибки
    });
}

// Функция для закрытия модального окна
function closeModal() {
    document.getElementById('editModal').style.display = 'none';
}




// кнопка добавить юзера
document.getElementById('userForm').addEventListener('submit', function(e) {
    e.preventDefault(); // Предотвратить стандартное поведение формы

    // Создание объекта FormData и заполнение его данными формы
    let formData = new FormData(this);

    // Использование Fetch API для отправки данных
    fetch('/add_user', {
        method: 'POST',
        body: formData, // отправляем данные из формы
    })
    .then(response => {
        if(response.ok) {
            // Получаем элементы по атрибуту name
            var usernameInput = document.querySelector('input[name="username"]');
            var passwordInput = document.querySelector('input[name="password"]');

            // Устанавливаем значение каждого элемента в пустую строку
            usernameInput.value = "";
            passwordInput.value = "";
            fetchUsers(); // Обновляем список пользователей
        }
        else{
            return response.text().then(text => { throw new Error(text) });
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert(error.message); // Показываем alert с текстом ошибки
    });
});

// удаление юзера
function deleteUser(username) {
    // Предотвратить действие по умолчанию при клике на ссылку
    event.preventDefault();
    
    // Использование Fetch API для отправки запроса на сервер
    fetch(`/delete_user?username=${username}`, {
        method: 'GET', // или 'DELETE', в зависимости от того, как настроен ваш сервер
    })
    .then(response => {
        if(response.ok) {
            fetchUsers(); // Обновляем список пользователей
        } else {
            return response.text().then(text => { throw new Error(text) });
        }
    })
    .then(data => {
        fetchUsers(); // Обновляем список пользователей
    })
    .catch(error => {
        alert(error.message); // Показываем alert с текстом ошибки
    });
}