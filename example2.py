from sqlize import AtomicSqlTable

lollys = AtomicSqlTable("Lollys", ['pop', 'color'])
lollys.new({'pop' : 'yes', 'color' : 'blue'})
lollys.new({'pop' : 'cicle', 'color' : 'blue'})
lollys.new({'pop' : 'aa', 'color' : 'red'})
lollys.new({'pop' : 'vv', 'color' : 'blue'})

print( lollys.get(id=None,keyvals={'color':'blue'}) )