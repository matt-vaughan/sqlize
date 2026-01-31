from sqlize import Sqlize, Bind

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