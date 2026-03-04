import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import StringVar
import asyncpg
import asyncio
import random
import os

class App:
    def __init__(self, root):
        self.root = root
        self.root.resizable(False, False)
        self.root.title("User Manager")

        self.db_config = {
            "host": os.getenv("DB_HOST"), # ip postgres
            "port": os.getenv("DB_PORT"), # port
            "user": os.getenv("DB_USER"), # username
            "password": os.getenv("DB_PASSWORD"), # pass
            "database": os.getenv("DB_NAME"), # db_name
        }
        self.search_results = []
        self.create_widgets()
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self.load_data())
        
        

    def search_users(self, username):
        self.search_results.clear()
        if username:
            search_query = f"SELECT * FROM users WHERE LOWER(username) LIKE LOWER('%{username}%')"
        else:
            search_query = "SELECT * FROM users"
        
        async def run_search():
            conn = await asyncpg.connect(**self.db_config)
            rows = await conn.fetch(search_query)
            self.search_results.extend(rows)
            self.treeview.delete(*self.treeview.get_children())
            await conn.close()
            for row in rows:
                row = [row["id"], row["username"], row["password"], row["route"]]
                self.treeview.insert('', 'end', values=row)
        self.loop.run_until_complete(run_search())

    def entry_username_changed(self, *args):
        # Получаем значение из поля ввода имени пользователя
        username = self.username_var.get()
        # Выполняем функцию поиска с переданным именем пользователя
        self.search_users(username)

    async def add_user(self):
        username = self.entry_username.get()
        password = self.entry_password.get()
        if len(username) < 4 or len(password) < 4:
            messagebox.showinfo(title="Внимание!", message="Логин или пароль имеет недопустимую длину!")
            return
        route = self.route_var.get()
        conn = await asyncpg.connect(**self.db_config)
        user_id = await conn.fetchval("SELECT id FROM users WHERE LOWER(username) = LOWER($1)", username)
        if user_id:
            messagebox.showinfo(title="Внимание!", message=f"Данный юзер уже есть в базе данных! Его id = {user_id}")
            return
        await conn.execute("INSERT INTO users (username, password, route) VALUES ($1, $2, $3)", username, password, route)
        await conn.close()
        await self.load_data()


    async def delete_user(self):
        username = self.entry_username.get()
        conn = await asyncpg.connect(**self.db_config)
        await conn.execute("DELETE FROM users WHERE LOWER(username) = LOWER($1)", username)
        await conn.close()
        await self.load_data()


    async def load_data(self):
        conn = await asyncpg.connect(**self.db_config)
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT,
                password TEXT,
                route TEXT
            )
        ''')
        
        rows = await conn.fetch("SELECT * FROM users ORDER BY username")
        await conn.close()
        for row in rows:
            row = [row["id"], row["username"], row["password"], row["route"]]
            self.treeview.insert('', 'end', values=row)

    def on_tree_select(self, event):
        selected = self.treeview.selection()[0] 
        data = self.treeview.item(selected)['values']
        self.entry_username.delete(0, tk.END)
        self.entry_password.delete(0, tk.END)
        self.entry_username.insert(tk.END, data[1])
        self.entry_password.insert(tk.END, data[2])
        self.route_var.set(data[3])

    def create_widgets(self):
        text = tk.Label(self.root, text="Логин")
        text.pack()
    

        self.username_var = StringVar()
        self.entry_username = tk.Entry(self.root, border=3, textvariable=self.username_var)
        self.username_var.trace("w", self.entry_username_changed)
        self.entry_username.pack(fill="both", padx=5, pady=5)

        text = tk.Label(self.root, text="Пароль")
        text.pack()
        self.password_frame = tk.Frame(self.root)
        self.password_frame.pack(fill="both")
        self.passwd_gen = tk.Button(self.password_frame, text="Сгенерировать", command=self.pass_generate, border=3)
        self.passwd_gen.pack(fill="both", side="right")
        self.entry_password = tk.Entry(self.password_frame, border=3)
        self.entry_password.pack(fill="both", padx=5, pady=5)



        text = tk.Label(self.root, text="Направление")
        text.pack()
        routes = ["MTT", "SPIN", "HOLDEM", "PLO", "ANOTHER"]
        self.route_var = tk.StringVar()
        self.route_var.set(routes[0])
        self.route_combobox = ttk.Combobox(self.root, textvariable=self.route_var, values=routes)
        self.route_combobox.pack(fill="both", padx=5, pady=5)

        self.button_add = tk.Button(self.root, text="Добавить пользователя", border=3, command=lambda: self.loop.run_until_complete(self.add_user()))
        self.button_add.pack(fill="both", padx=5, pady=5)
        self.button_delete = tk.Button(self.root, text="Удалить пользователя", border=3, command=lambda: self.loop.run_until_complete(self.delete_user()))
        self.button_delete.pack(fill="both", padx=5, pady=5)

        columns=('ID', 'Username', 'Password', "Route")
        self.rev = {"#%d"%x:False for x in range(1,len(columns)+1)}
        self.treeview = ttk.Treeview(self.root, columns=columns, show='headings')
        self.treeview.heading('ID', text='ID', command=lambda: self.treeview_sort_column("#1"))
        self.treeview.heading('Username', text='Username', command=lambda: self.treeview_sort_column("#2"))
        self.treeview.heading('Password', text='Password', command=lambda: self.treeview_sort_column("#3"))
        self.treeview.heading('Route', text='Route', command=lambda: self.treeview_sort_column("#4"))
        self.treeview.pack(fill="both", padx=5, pady=5)
        self.treeview.bind('<Double-1>', self.on_tree_select)  


    def treeview_sort_column(self, col):
        l = [(self.treeview.set(k, col), k) for k in self.treeview.get_children('')]
        l.sort(reverse=self.rev[col])
        for k in self.rev.keys():
            self.treeview.heading(k,text=self.treeview.heading(k,"text").replace("v","").replace("^",""))
        self.treeview.heading(col,text=["^","v"][self.rev[col]]+self.treeview.heading(col,"text"))
        self.rev[col]=not self.rev[col]
        for index, (val, k) in enumerate(l):
            self.treeview.move(k, '', index)


    def pass_generate(self):
        # генератор пароля
        password = ''.join(list(map(lambda sym: list(map(chr, list(range(48, 58))+list(range(65, 91))+list(range(97, 123))))[random.randint(0, 61)], list(range(6)))))
        self.entry_password.delete(0, tk.END)
        self.entry_password.insert(tk.END, password)

if __name__ == "__main__":
    root = tk.Tk()
    root.resizable(False, False)
    try:
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        root.wm_iconbitmap(os.path.join(base_path, "icon.ico"))
    except:
        pass
    app = App(root)
    root.mainloop()
