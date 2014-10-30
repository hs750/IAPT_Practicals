# @IAPT: Begin by connecting to the database - if you don't have one named store.db in the databases directory, then
# you will automatically have one created for you
db = DAL('sqlite://store.db')

# -*- coding: utf-8 -*-

#########################################################################
## Here is sample code if you need for
## - email capabilities
## - authentication (registration, login, logout, ... )
## - authorization (role based authorization)
## - services (xml, csv, json, xmlrpc, jsonrpc, amf, rss)
## - old style crud actions
## (more options discussed in gluon/tools.py)
#########################################################################

from gluon.tools import Auth, Service, PluginManager

auth = Auth(db)
service = Service()
plugins = PluginManager()

## create all tables needed by auth if not custom tables
auth.define_tables(username=False, signature=False)

## configure email
mail = auth.settings.mailer
mail.settings.server = 'logging' if request.is_local else 'smtp.gmail.com:587'
mail.settings.sender = 'you@gmail.com'
mail.settings.login = 'username:password'

## configure auth policy
auth.settings.registration_requires_verification = False
auth.settings.registration_requires_approval = False
auth.settings.reset_password_requires_verification = True

## if you need to use OpenID, Facebook, MySpace, Twitter, Linkedin, etc.
## register with janrain.com, write your domain:api_key in private/janrain.key
from gluon.contrib.login_methods.janrain_account import use_janrain
use_janrain(auth, filename='private/janrain.key')

#########################################################################
## Define your tables below (or better in another model file) for example
##
## >>> db.define_table('mytable',Field('myfield','string'))
##
## Fields can be 'string','text','password','integer','double','boolean'
##       'date','time','datetime','blob','upload', 'reference TABLENAME'
## There is an implicit 'id integer autoincrement' field
## Consult manual for more options, validators, etc.
##
## More API examples for controllers:
##
## >>> db.mytable.insert(myfield='value')
## >>> rows=db(db.mytable.myfield=='value').select(db.mytable.ALL)
## >>> for row in rows: print row.id, row.myfield
#########################################################################

## after defining tables, uncomment below to enable auditing
# auth.enable_record_versioning(db)



# @IAPT: Now we need to define a simple set of tables.  There are two tables - 1 for the products, and 1 for the
# features.  The field 'id' will be automatically added to the table as a primary key.  If you want some other field
# to be primary key there are ways to overrride that.  See the Web2Py book for details on how to do that.
db.define_table('products', Field('name'), Field('price'), Field('type'), Field('description'), Field('publisher'))

# @IAPT: For the features we are going to set up a foreign key.  Now, remember that a foreign key equates to a 1-many
# relationship in our data model, so we will simply refer to the table that we want to match things to.  Web2Py will
# then automatically set up the foreign key for us.  Pretty simple.
db.define_table('features', Field('product_id', db.products))

# @IAPT: After running your website 1 time, you will automatically have created the above two tables that are empty
# of data.  Be aware - once you start modifying stuff - it can (very rarely) go very wrong.  Migrations will happen automatically,
# and there are several "gotchas" that are documented in the Data Abstraction Layer of Web2Py you should be aware
# of for working with SQLite.
