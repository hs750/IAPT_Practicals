db = DAL("sqlite://store.db")


db.define_table('products', Field('name', 'string'), Field('ptype', 'string'),
                Field('description', 'string', length=10240), Field('price', 'decimal(0,100'),
                Field('publisher', 'string'))


db.define_table('features', Field('product_id'))