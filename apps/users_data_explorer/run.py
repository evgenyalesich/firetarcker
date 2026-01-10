import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QCalendarWidget, QTableWidget, QTableWidgetItem, QPushButton, QVBoxLayout, QWidget, QComboBox, QLineEdit, QHBoxLayout, QLabel, QFileDialog, QMessageBox
from PyQt5.QtGui import QIcon
from subprocess import Popen
import re
import os

class ExplorerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.date_constraint = None
        self.widget = QWidget()
        self.icon_path = "icon.png"
        self.setWindowIcon(QIcon(self.icon_path))
        self.widget.setWindowIcon(QIcon(self.icon_path))

        # Пытаемся открыть файл и проверить путь
        try:
            with open("path.conf", "r") as file:
                self.dir_path = file.read().strip()
            if not os.path.exists(self.dir_path):
                raise FileNotFoundError
        except FileNotFoundError:
            msgBox = QMessageBox(self.widget)
            msgBox.setWindowTitle("Невозможно найти папку")
            msgBox.setText("Файл path.conf отсутствует или путь в нём недействителен.\nПожалуйста, выберите папку с каталогами юзеров!\n\nЕсли вы указали неверную папку, удалите файл path.conf в директории программы, и перезапустите её!")
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.addButton("Выбрать папку", QMessageBox.AcceptRole)
            msgBox.addButton("Выход", QMessageBox.RejectRole)
            if msgBox.exec_() == QMessageBox.AcceptRole:
                self.dir_path = get_directory_path(self.widget)
                if not self.dir_path:  # Пользователь отменил выбор
                    sys.exit()
                with open("path.conf", "w") as file:
                    file.write(self.dir_path)
            else:
                sys.exit()

        self.users_data = self.load_users_data()
        self.initUI()



    def initUI(self):
        # инициализация ГУИ-шных элементов
        self.setWindowTitle("FireStormTrackerExplorer")
        self.setGeometry(100, 100, 1000, 600)
        
        main_layout = QVBoxLayout()

        # Фильтр username и выбор даты
        self.date_label = QLabel("Дата от:")
        self.button_start = DateButton('Выбрать дату', parent=self, dialog_title="Начальная дата")
        self.button_end = DateButton('Выбрать дату', parent=self, dialog_title="Конечная дата")
        self.date_label2 = QLabel("Дата до:")
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.date_label)
        filter_layout.addWidget(self.button_start)
        filter_layout.addWidget(self.date_label2)
        filter_layout.addWidget(self.button_end)
        
        self.filter_username = QLineEdit()
        self.filter_username.setPlaceholderText("Поиск по username")
        self.filter_username.textChanged.connect(self.filter_display)

        self.global_room_selector = QComboBox()
        self.global_room_selector.addItem("Любой рум")
        self.global_room_selector.addItems(self.get_unique_rooms())
        self.global_room_selector.currentIndexChanged.connect(self.filter_display)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.filter_username)
        controls_layout.addWidget(self.global_room_selector)

        self.table = QTableWidget()
        self.table.setColumnCount(4)  # Username, Room, Date, Open folder
        self.table.setHorizontalHeaderLabels(['Юзер', 'Рум', 'Дата выгрузки', 'Открыть папку'])
        self.table.horizontalHeader().setStretchLastSection(True)
        
        main_layout.addLayout(controls_layout)
        main_layout.addLayout(filter_layout)
        main_layout.addWidget(self.table)
        
        
        self.widget.setLayout(main_layout)
        self.setCentralWidget(self.widget)
        
        self.filter_display()

    def filter_dates(self):
        
        if self.button_start.date and not self.button_end.date:
            self.button_end.setText(self.button_start.date.toString("yyyy-MM-dd"))
            self.button_end.date = self.button_start.date

        elif not self.button_start.date and self.button_end.date:
            self.button_start.setText(self.button_end.date.toString("yyyy-MM-dd"))
            self.button_start.date = self.button_end.date

        elif not self.button_start.date and not self.button_end.date:
            return

        start_date = self.button_start.date
        end_date = self.button_end.date

        start_date_int = int(start_date.toString("yyyyMMdd"))
        end_date_int = int(end_date.toString("yyyyMMdd"))
        for row in range(self.table.rowCount() - 1, -1, -1):
            date_widget = self.table.cellWidget(row, 2)
            if isinstance(date_widget, QComboBox):
                valid_dates = []
                for i in range(1, date_widget.count()):
                    date_str = date_widget.itemText(i)
                    date_int = int(date_str.replace("-", ""))
                    if start_date_int <= date_int <= end_date_int:
                        valid_dates.append(date_str)

                if valid_dates:
                    date_widget.clear()
                    date_widget.addItem("Выберите дату")
                    date_widget.addItems(valid_dates)
                    # делаем активным последний элемент вып. списка
                    date_widget.setCurrentIndex(date_widget.count()-1)
                else:
                    self.table.removeRow(row)
            else:
                self.table.removeRow(row)

    def check_date_constraints(self):
        if self.button_start.date and self.button_end.date:
            if self.button_start.date > self.button_end.date:
                self.reset_invalid_date()

    def reset_invalid_date(self):
        self.button_end.setText(self.button_start.date.toString("yyyy-MM-dd"))
        self.button_end.date = self.button_start.date
        self.filter_display()

    def load_users_data(self):
        users_data = {}
        for user in os.listdir(self.dir_path):
            user_path = os.path.join(self.dir_path, user)
            if not os.path.isdir(user_path):
                continue
            users_data[user] = {}
            for room in os.listdir(user_path):
                room_path = os.path.join(user_path, room)
                if os.path.isdir(room_path):
                    users_data[user][room] = os.listdir(room_path)
        return users_data

    def get_unique_rooms(self):
        rooms = set()
        for user, user_rooms in self.users_data.items():
            rooms = rooms.union(set(user_rooms.keys()))
        return sorted(rooms)

    def filter_display(self):
        filtered_data = [(user, rooms) for user, rooms in self.users_data.items() if self.filter_username.text().lower() in user.lower()]
        self.table.setRowCount(0)  # Очистить таблицу

        global_room_selection = self.global_room_selector.currentText()

        for user, rooms in filtered_data:
            if global_room_selection != "Любой рум" and global_room_selection not in rooms.keys():
                continue

            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            self.table.setItem(row_position, 0, QTableWidgetItem(user))

            if global_room_selection == "Любой рум":
                room_combobox = QComboBox()
                room_combobox.addItem("Выбери рум")
                room_combobox.addItems(rooms.keys())
                self.table.setCellWidget(row_position, 1, room_combobox)

                date_combobox = QComboBox()
                date_combobox.addItem("Выберите дату")
                room_combobox.currentIndexChanged[str].connect(lambda room, row=row_position, user=user: self.update_dates(row, user, room))
                self.table.setCellWidget(row_position, 2, date_combobox)
            else:
                self.table.setItem(row_position, 1, QTableWidgetItem(global_room_selection))
                self.update_dates(row_position, user, global_room_selection, init=True)

            open_button = QPushButton("Открыть")
            open_button.clicked.connect(lambda checked, user=user: self.open_folder(user))
            self.table.setCellWidget(row_position, 3, open_button)

        self.filter_dates()

    def update_dates(self, row, user, room, init=False):
        if room == "Выбери рум" or room not in self.users_data[user].keys():
            return
        date_combobox = self.table.cellWidget(row, 2) if not init else QComboBox()
        date_combobox.clear()
        date_combobox.addItem("Выберите дату")

        date_pattern = re.compile(r"\d{4}-\d{2}-\d{2}")  # Регулярное выражение для даты в формате YYYY-MM-DD
        valid_dates = [date for date in self.users_data[user][room] if date_pattern.match(date)]
        date_combobox.addItems(valid_dates)

        if init:
            self.table.setCellWidget(row, 2, date_combobox)

    def user_row(self, user):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == user:
                return row
        return None

    def open_folder(self, user):
        row = self.user_row(user)
        
        room_widget = self.table.cellWidget(row, 1)
        if isinstance(room_widget, QComboBox):
            room = room_widget.currentText() if room_widget.currentIndex() > 0 else ""
        else:
            room = self.table.item(row, 1).text() if self.table.item(row, 1) else ""

        date_widget = self.table.cellWidget(row, 2)
        if isinstance(date_widget, QComboBox):
            date = date_widget.currentText() if date_widget.currentIndex() > 0 else ""
        else:
            date = self.table.item(row, 2).text() if self.table.item(row, 2) else ""
        
        folder_path = os.path.join(self.dir_path, user, room if room != "Выбери рум" else "", date if date != "Выберите дату" else "")
        if os.path.exists(folder_path):
            Popen(f'explorer "{folder_path}"', shell=True)
        else:
            print("Directory does not exist:", folder_path)

class DateButton(QPushButton):
    def __init__(self, title, dialog_title, parent=None):
        super(DateButton, self).__init__(title, parent)
        self.dialog = CalendarDialog(dialog_title, self.date_constraint_func, self)
        self.date = None
        self.clicked.connect(self.show_dialog)
        self.parent = parent

    def show_dialog(self):
        self.dialog.exec_()

    def set_date(self, date):
        self.date = date
        self.setText(date.toString("yyyy-MM-dd"))
        self.parent.check_date_constraints()
        self.parent.filter_display()

    def date_constraint_func(self, other_date):
        return other_date

class CalendarDialog(QDialog):
    def __init__(self, title, constraint_func=None, parent=None):
        super(CalendarDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.constraint_func = constraint_func
        self.calendar = QCalendarWidget(self)
        self.calendar.clicked.connect(self.handle_date_selected)
        layout = QVBoxLayout(self)
        layout.addWidget(self.calendar)

    def handle_date_selected(self, date):
        if self.constraint_func:
            if not self.constraint_func(date):
                return
        self.parent().set_date(date)
        self.accept()

def get_directory_path(parent=None):
    """Возвращает пользовательский путь к папке или None."""
    dialog = QFileDialog(parent)
    dialog.setFileMode(QFileDialog.Directory)
    dialog.setOption(QFileDialog.ShowDirsOnly, True)
    if dialog.exec_() == QFileDialog.Accepted:
        return dialog.selectedFiles()[0]
    return None

def main():
    app = QApplication(sys.argv)        
    ex = ExplorerApp()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()


"""
НУЖНО ДОБАВИТЬ:
-считывать в dates юзера все его даты из всех румов, если room == "Выбери рум"
"""