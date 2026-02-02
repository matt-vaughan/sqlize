import time
from sqlize import AtomicDatabase, AtomicSqlTable
"""
This is an example of how to use my AtomicSqlTable class...
if you want to use this, let me know at mvaughan404@gmail.com
I'm much more likely to support this repo if it's getting some use
"""
# connect to my database
db = AtomicDatabase('tests.db')
# create my four tables
lolly = db.table("Lollys", [('variety','TEXT'), ('color','TEXT'),('number','INT')], True)
order = db.table("Orders", [('date', 'INT'),('user_id', 'INT')], True)
purchase = db.table("Purchases",[('lolly_id', 'INT'),('quantity','INT'),('order_id', 'INT')], True )
user = db.table("Users", [('name','TEXT'),('email','TEXT')], True)

# create four lollys for sale
l1 = lolly.new({'variety' : 'round', 'color' : 'blue', 'number' : 5})
l2 = lolly.new({'variety' : 'square', 'color' : 'blue', 'number' : 10})
l3 = lolly.new({'variety' : 'big', 'color' : 'red', 'number' : 15})
l4 = lolly.new({'variety' : 'swirled', 'color' : 'many', 'number' : 20})

# create a user
u1 = user.new({'name': "Vlad VonBurton", 'email': 'vvb@example.com'})

# create an order 
o1 = order.new({'date': time.time_ns(), 'user_id' : u1 })

# with two items
p1 = purchase.new({ 'lolly_id' : l1, 'quantity' : 5, 'order_id': o1})
p2 = purchase.new({ 'lolly_id' : l2, 'quantity' : 3, 'order_id': o1})


print( "Getting all lollys with color=blue\n", lolly.get(id=None,keyvals={'color':'blue'}) )
print( "Getting the lolly with id=1", lolly[1] )
print( "Getting the order and finding the items in it")
o_id, o_date, o_user = order[o1]
ps = purchase.get(id=None, keyvals={'order_id' : o_id})
print("order id ", o_id," user_id ", o_user," who is ",u1, "\n", ps)
print("updating a quantity")
purchase.update(ps[0][0], 'quantity', 20)
print( purchase[ps[0][0]] ),