__author__ = 'Harrison'

db = DAL("sqlite://recipe.db")


db.define_table('recipes', Field('name', 'string'), Field('instructions', 'string', length=10240),
                Field('source', 'string'), Field('serving', 'integer'),
                Field('cooktime', 'integer'), Field('preptime', 'integer'), Field('difficulty', 'integer'))


db.define_table('ingredients', Field('name', 'string'), Field('calories', 'decimal(5,2)'),
                Field('sugar', 'decimal(5,2)'), Field('fat', 'decimal(5,2)'),
                Field('satfat', 'decimal(5,2)'), Field('salt', 'decimal(5,2)'))

db.define_table('recipeingredient', Field('recipe_id', db.recipes),
                Field('ingredient_id', db.ingredients))
