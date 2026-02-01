from sqlize import AtomicSqlTable

lollys = AtomicSqlTable("Lollys", [('pop','TEXT'), ('color','TEXT'),('number','INT')], True)
lollys.new({'pop' : 'yes', 'color' : 'blue', 'number' : 5})
lollys.new({'pop' : 'cicle', 'color' : 'blue', 'number' : 10})
lollys.new({'pop' : 'aa', 'color' : 'red', 'number' : 15})
lollys.new({'pop' : 'vv', 'color' : 'blue', 'number' : 20})

print( lollys.get(id=None,keyvals={'color':'blue'}) )