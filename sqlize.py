import hashlib
import secrets
import sqlite3
import inspect
import functools
import inspect
import time


def tuple_flatten(lst):
    return ( *lst ,) 

print( tuple_flatten([4,3,2,(1),0]) )
def andComb( lst ):
    if lst == []:
        return ""
    elif len(lst) == 1:
        return f"{lst[0]}"
    else:
        a, *b = lst
        return f"{a} AND " + andComb(b)

class Bind:
    @staticmethod
    def store(table, bindings):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                # run the function, do the update
                result = func(self, *args, **kwargs)

                db = self.__class__._database
                cursor = db.cursor()

                bind_line = ", ".join([f"{binding} = ?" for binding in bindings])
                query = f'''UPDATE {table} SET {bind_line} WHERE id = ?'''
                cursor.execute(query,(*([self.__getattribute__(binding) for binding in bindings]+[self.id]), ))
                return result
            return wrapper
        return decorator

    @staticmethod
    def load(table, bindings):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                db = args[0].__getattribute__('__class__')._database
                cursor = db.cursor()

                query = f'''SELECT {",".join([f"{b}" for b in bindings])} FROM {table} WHERE id = ?'''
                cursor.execute(query, (args[0].__getattribute__('id'),))
                
                rows = cursor.fetchall()
                if len(rows) > 0:
                    for i, binding in enumerate(bindings):
                        args[0].__setattr__(binding, rows[0][i])
                            
                return func(*args, **kwargs)
            return wrapper
        return decorator

class Sqlize(type):
    _database = None
    def __new__(cls, name, bases, dct):
        if not cls._database:
            cls._database = sqlite3.connect('temp.db')
        
        sig = inspect.signature(dct['__init__'])
        fields = [name for name, parameter in sig.parameters.items() if name != "self"]
        cls.make(name.lower()+"s", fields)
        
        return super().__new__(cls, name, bases, dct)
        
    
    def items(self):
        cls = self.__class__
        sig = inspect.signature(self.__init__)
        fields = ['id'] + [name for name, parameter in sig.parameters.items() if name != "self" and name != "args" and name != "kwargs"]
        
        query = f'''SELECT {",".join(fields)} FROM {self.__name__.lower()+"s"}'''
        
        cursor = cls._database.cursor()
        cursor.execute(query)
        
        rows = cursor.fetchall()
        items = []
        for row in rows:
            item = self( *row[1:] )
            item.id = row[0]
            items.append(item)
        
        return items
    
    @classmethod
    def make(cls, table, fields):
        cursor = cls._database.cursor()
        cursor.execute(f'DROP TABLE IF EXISTS {table}')
        cursor.execute(f'''
                        CREATE TABLE IF NOT EXISTS {table} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        {", ".join([f"{field} TEXT" for field in fields])}
                        )
                        ''')
        cursor.close()

    @classmethod
    def show_tables(cls):
        cursor = cls._database.cursor()
        query = f'''SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name''';
        cursor.execute(query)
        return cursor.fetchall()
    
    @classmethod
    def table(cls, table):
        cursor = cls._database.cursor()
        query = f'''SELECT * FROM {table}''';
        cursor.execute(query)
        return cursor.fetchall()
    
    @classmethod
    def entries(cls, table, key_values):
        keys = [f"{k}=?" for k, _ in key_values]
        values = (*[v for _, v in key_values],)
        cursor = cls._database.cursor()
        query = f'''SELECT * FROM {table} WHERE ''' + " AND ".join(keys)
        print(query)
        cursor.execute(query, values)
        return cursor.fetchall()
    
    @classmethod
    def insert(cls, table, key_values):
        keys = [f"{k}" for k, _ in key_values]
        values = (*[v for _, v in key_values],)
        qmarks = ",".join(["?" for kv in key_values])
        query = f'''INSERT OR IGNORE INTO {table} ({",".join(keys)}) VALUES ({qmarks})'''
        cursor = cls._database.cursor()
        cursor.execute(query, values)
        return cursor.lastrowid, cursor.fetchall()
    
    @classmethod
    def update(cls, table, key_values, id):
        bind_line = ", ".join([f"{k} = ?" for k,_ in key_values])
        query = f'''UPDATE {table} SET {bind_line} WHERE id = ?'''
        cursor = cls._database.cursor()
        cursor.execute(query, (*[v for _,v in key_values], id))
        

class Login(metaclass=Sqlize):
    def __init__(self, date, userid, success):
        self.date = date
        self.userid = userid
        self.success = success
        
        entries = Login.entries("logins", [('date',date),('userid',userid),('success',success)])
        if not entries or entries == []:
            self.id, _ = Login.insert("logins", [('date',date),('userid',userid),('success',success)])
        else:
            self.id = entries[0][0]
            
    @Bind.store("logins", ["date", "userid", "success"])
    def set(self, date, userid, success):
        if date:
            self.date = date
        if userid:
            self.userid = userid
        if success:
            self.success = success

    @Bind.load("logins",  ["date", "userid", "success"])
    def get(self):
        return (self.date, self.userid, self.success)

class User(metaclass=Sqlize):
    def __init__(self, name, phone, email, password, salt=None): # salt included so it will be in database
        self.name = name
        self.phone = phone
        self.email = email
        self.salt = secrets.token_hex(16)
        self.password = hashlib.sha256((password + self.salt).encode()).hexdigest()
        
        entries = User.entries("users", [('name',name),('phone',phone)])
        # create the user in db if name, phone pair doesn't exist
        if not entries or entries == []:
            self.id, _ = User.insert("users", [('name',name),('phone',phone),('email',email),('password',self.password),('salt',self.salt)])
        else:
            self.id = entries[0][0]

    @Bind.load("users", ["salt", "password"])
    def login(self, password):
        match = self.password == hashlib.sha256((password + self.salt).encode()).hexdigest()
        return Login( time.time_ns(), self.id, match )

    @Bind.store("users", ["name"])
    def set_name(self, name):
        self.name = name

    @Bind.load("users", ["name"])
    def get_name(self):
        return self.name

    @Bind.store("users", ["phone"])
    def set_phone(self, phone):
        self.phone = phone
    
    @Bind.load("users", ["phone"])
    def get_phone(self):
        return self.phone

    @Bind.store("users", ["name", "phone", "email"])
    def set(self, name, phone, email):
        self.name = name
        self.phone = phone
        self.email = email

    @Bind.load("users", ["name", "phone", "email"])
    def get(self):
        return (self.name, self.phone, self.email)
        

n = User("H", 9783878782, "bob@example.com","temp")
n.set("A", 44, "bill@example.com")
print(n.get_name())
print(n.id)
n.set("Assy", 5551212, "andy@gmail.com")
print(n.get())
m = User("PP", 5551122, "pp@example.com", "another")
l = Login("12/11/12", "1", "0")

user_list = User.items()

while True:
    do = input("Would you like to (s)how all table names, (p)rint a table, (l)ookup something, log(o)n, (u)pdate, (q)uit\n")
    try:
        match do.lower():
            case 's': 
                print(User.show_tables())
            case 'p':
                table_name = input("Input table name\n") 
                print(User.table(table_name))
            case 'l':
                table_name = input("Input table name\n") 
                where = input("write your statement as column=value,column2=value2\n")
                keyvals = [(s[0], s[1]) for s in [str.split("=") for str in where.split(",")]]
                print(User.entries('users', keyvals))
            case 'u':
                table_name = input("Input table name\n")
                commasep = input("Input three comma separated fields\n")
                if table_name == "users":
                    result = User( *commasep.split(","), )
                if table_name == "logins":
                    result = Login( *commasep.split(","), )
                print( result )
            case 'o':
                username = input("Enter the username\n")
                password = input("Enter the password\n")
                for user in user_list:
                    if user.get_name() == username:
                        login = user.login(password)
                        print(f"Attempted login on {login.date} with userid {login.userid}. Success: {login.success}")
                        
            case 'q':
                exit()
    except sqlite3.OperationalError:
        print("Continueing after SQL error")