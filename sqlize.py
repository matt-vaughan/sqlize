from abc import ABC
import hashlib
import secrets
import sqlite3
import inspect
import functools
import inspect
import time

DB_NAME = "temp.db"

"""
Sqlize is the metaclass you use when making a class
For all of your parameters to __init__ for your class, there will be a field
in the database. The table will automatically be generated, so will the entries,
and updates can be pushed automatically with the use of the Bind class

OR

Use AtomicSqlTable to 
"""
class Atomic(type):
    _database = None
    def __new__(cls, name, bases, dct):
        if not cls._database:
            cls._database = sqlite3.connect(DB_NAME)    
        return super().__new__(cls, name, bases, dct)
    
    @classmethod
    def query(cls, query, params=None):
        cursor = cls._database.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        return result
    
class AtomicSqlTable(metaclass=Atomic):
    def __init__(self, table, fields):
        self.table = table
        self.fields = fields
        cursor = self.__class__._database.cursor()
        query = f'''
        CREATE TABLE IF NOT EXISTS {table} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        {", ".join([f"{field} TEXT" for field in fields])}
        )
        '''
        self.__class__.query(query, ())

    def valuesAndParams(self, keyvals : dict):
        where = " AND ".join([f"{k}=?" for k in keyvals.keys()])
        params = [v for v in keyvals.values()]
        keys = ",".join([f"{k}" for k in keyvals.keys()])
        qmarks = ",".join([f"?" for _ in keyvals.keys()])
        return where, ( *params , ), keys, qmarks
    
    def new(self, keyvals):
        _, params, keys, qmarks = self.valuesAndParams(keyvals)
        query = f'INSERT OR IGNORE INTO {self.table} ({keys}) VALUES ({qmarks})'
        return self.__class__.query(query, params)

    def update(self, id, key, value):
        query = f'UPDATE {self.table} SET {key}=? WHERE id = ?'
        result = self.__class__.query(query, (value, id))
        return result
    
    def get(self, id=None, keyvals=None):
        if id:
            query = f'SELECT * FROM {self.table} WHERE id=?'
            return self.query(query, (id))
        elif keyvals:
            where, params, _, _ = self.valuesAndParams(keyvals)
            query = f'SELECT * FROM {self.table} WHERE {where}'
            return self.__class__.query(query, params)

def tuple_flatten(lst):
    return ( *lst ,) 

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
            cls._database = sqlite3.connect(DB_NAME)
        
        # get the arguments to __init__
        sig = inspect.signature(dct['__init__'])
        fields = [name for name, _ in sig.parameters.items() if name != "self" and name != "args" and name != "kwargs"]
        
        # make the table if it's not in the db
        cls.make(name.lower()+"s", fields)
        
        return super().__new__(cls, name, bases, dct)
        
    # generate a list of regular class instances for each row in the database
    # leave as instance method due to invokation specifics
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
    
    # make the database table if it dpes not exists
    @classmethod
    def make(cls, table, fields):
        cursor = cls._database.cursor()
        params = ", ".join([f"{field} TEXT" for field in fields])
        cursor.execute(f'''
                        CREATE TABLE IF NOT EXISTS {table} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        {params}
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
        
