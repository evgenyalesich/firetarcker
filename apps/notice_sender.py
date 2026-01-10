import tkinter as tk
from tkinter import ttk, messagebox
import asyncpg
import os
import asyncio

# переходим по указанному пути
if os.getenv("ROOT_DIR"):
    os.chdir(os.getenv("ROOT_DIR"))

DB_CONFIG = {
    "host": os.getenv("DB_HOST"), # ip postgres
    "port": os.getenv("DB_PORT"), # port
    "user": os.getenv("DB_USER"), # username
    "password": os.getenv("DB_PASSWORD"), # pass
    "database": os.getenv("DB_NAME"), # db_name
}

async def async_load_data_from_db():
    conn = await asyncpg.connect(**DB_CONFIG)
    rows = await conn.fetch("SELECT username, route FROM users")
    await conn.close()
    users_data = []
    for _ in rows:
        username = _["username"]
        route = _["route"]
        users_data.append([username, route])

    return users_data

def load_data_from_db():
    return asyncio.run(async_load_data_from_db())

def set_values_from_tree(event):
    selected_item = tree.item(tree.focus())['values']
    if selected_item:
        username, route = selected_item
        user_entry.delete(0, tk.END)
        user_entry.insert(0, username)  
        route_combobox.set(route)  

async def async_create_notice_files(selected_option, user_input, text_input, routes):
    notice_directory = "notice"
    if not os.path.exists(notice_directory):
        os.makedirs(notice_directory)

    
    if selected_option == "specific_user":
        file_path = os.path.join(notice_directory, f"{user_input}.txt")
        with open(file=file_path, mode='w', encoding="utf-8") as f:
            f.write(text_input)
    elif selected_option == "all_users":
        conn = await asyncpg.connect(**DB_CONFIG)
        users = await conn.fetch("SELECT username FROM users")
        await conn.close()
        for username, in users:
            file_path = os.path.join(notice_directory, f"{username}.txt")
            with open(file=file_path, mode='w', encoding="utf-8") as f:
                f.write(text_input)
    elif selected_option == "by_route":
        conn = await asyncpg.connect(**DB_CONFIG)
        users = await conn.fetch("SELECT username FROM users WHERE route = $1", routes)
        await conn.close()
        for username, in users:
            file_path = os.path.join(notice_directory, f"{username}.txt")
            with open(file=file_path, mode='w', encoding="utf-8") as f:
                f.write(text_input)

def create_notice_files(selected_option, user_input, text_input, routes):
    return asyncio.run(async_create_notice_files(selected_option, user_input, text_input, routes))

root = tk.Tk()
root.title("Уведомления для пользователей")
root.geometry("520x520")
root.resizable(True, True)

style = ttk.Style()
style.theme_use("clam")

# Создание Treeview таблицы
main = ttk.Frame(root, padding=10)
main.grid(row=0, column=0, sticky="nsew")
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

tree = ttk.Treeview(main, columns=('Username', 'Route'), show='headings', height=8)
tree.heading('Username', text='Username')
tree.heading('Route', text='Route')
tree.grid(row=0, column=0, columnspan=3, sticky="nsew")
tree.bind('<Double-1>', set_values_from_tree)
main.rowconfigure(0, weight=1)
main.columnconfigure(1, weight=1)

# функция для асинхронной загрузки данных в Treeview
def load_data_to_treeview():
    rows = load_data_from_db()
    for user in rows:
        tree.insert('', tk.END, values=user)

# # функция для выполнения корутины async_load_data_to_treeview
# def load_data_to_treeview():
#     asyncio.run(async_load_data_to_treeview())

# root.after_idle(load_data_to_treeview)
load_data_to_treeview()

# Вариант выбора пользователя
user_choice = tk.StringVar(value="all_users")

frame_two = ttk.LabelFrame(main, text="Кому отправить", padding=6)
frame_two.grid(row=1, column=0, columnspan=3, sticky="we", pady=(10, 4))
ttk.Radiobutton(frame_two, text="Всем юзерам", variable=user_choice, value="all_users").pack(anchor="w")


# Radiobuttons
frame_one = ttk.Frame(main)
frame_one.grid(row=2, column=0, columnspan=3, sticky="we", pady=4)
ttk.Radiobutton(frame_one, text="Конкретному юзеру", variable=user_choice, value="specific_user").pack(side="left")
user_entry = ttk.Entry(frame_one)
user_entry.pack(side="left", fill="x", expand=True, padx=(6, 0))

frame_three = ttk.Frame(main)
frame_three.grid(row=3, column=0, columnspan=3, sticky="we", pady=4)

unique_routes = list(set(route for _, route in load_data_from_db()))
unique_routes.sort() 
ttk.Radiobutton(frame_three, text="Всем по направлению", variable=user_choice, value="by_route").pack(side="left")
route_combobox = ttk.Combobox(frame_three, values=unique_routes, state="readonly")
route_combobox.pack(side="left", fill="x", expand=True, padx=(6, 0))
if unique_routes:
    route_combobox.current(0)


text_label = ttk.Label(main, text="Текст уведомления")
text_label.grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 4))
text_input = tk.Text(main, height=10)
text_input.grid(row=5, column=0, columnspan=3, sticky="nsew")
main.rowconfigure(5, weight=1)

# Кнопка отправки
def send_notice():
    selected_option = user_choice.get()
    user_input = user_entry.get()
    text_content = text_input.get("1.0", "end-1c")
    routes = route_combobox.get() if route_combobox.get() != "" else None
    if not text_content.strip():
        messagebox.showwarning("Внимание", "Текст уведомления пустой.")
        return
    create_notice_files(selected_option, user_input, text_content, routes)
    messagebox.showinfo("Готово", "Уведомление подготовлено.")

send_button = ttk.Button(main, text="Отправить", command=send_notice)
send_button.grid(row=6, column=0, columnspan=3, sticky="we", pady=(8, 0))

# Запуск основного цикла tkinter
root.mainloop()
