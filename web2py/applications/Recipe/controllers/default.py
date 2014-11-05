def index():
    return dict()


def addIngredient():
    addin = getIngredientForm();
    if addin.accepts(request, session):
        db.ingredients.insert(name=request.vars.ingredient_name, calories=request.vars.ingredient_calories,
                              sugar=request.vars.ingredient_sugar, fat=request.vars.ingredient_fat,
                              satfat=request.vars.ingredient_satfat, salt=request.vars.ingredient_salt)
        db.commit
        response.flash = "Ingredient " + request.vars.ingredient_name + " added to database"
        print(BEAUTIFY(request.vars))
    elif addin.errors:
        response.flash = "There was an error, perhaps one of the fields is blank"
        print("Errors")
    else:
        response.flash = "Enter the details of the ingredient you would like to add"
        print("pther")

    return dict(addIngredient=addin)

def addRecipe():
    addrecipe = getRecipeForm()
    searchIngredient = FORM('Search Ingredient',
                            INPUT(_name='search_ingredient', _type='search', requires=IS_NOT_EMPTY()),
                            INPUT(_type='submit'))
    newIngredient = FORM(BUTTON('Add New Ingredient', _type='submit'))
    addingredient = None
    if newIngredient.accepts(request, session):
        addingredient = getIngredientForm()

    return dict(addRecipe=addrecipe, addIngredient=addingredient, searchIngredient=searchIngredient, newIngredient=newIngredient)

def getIngredientForm():
    iForm = FORM(DIV(LABEL('Ingredient Name:', _for='ingredient_name')),
                 DIV(INPUT(_name='ingredient_name', requires=IS_NOT_EMPTY())),
                 DIV(LABEL('Ingredient Calories:', _for='ingredient_calories')),
                 DIV(INPUT(_name='ingredient_calories', _type='number', requires=IS_NOT_EMPTY())),
                 DIV(LABEL('Ingredient Sugar:', _for='ingredient_sugar')),
                 DIV(INPUT(_name='ingredient_sugar', _type='number', requires=IS_NOT_EMPTY())),
                 DIV(LABEL('Ingredient Fat:', _for='ingredient_fat')),
                 DIV(INPUT(_name='ingredient_fat', _type='number', requires=IS_NOT_EMPTY())),
                 DIV(LABEL('Ingredient Saturated Fat:', _for='ingredient_satfat')),
                 DIV(INPUT(_name='ingredient_satfat', _type='number', requires=IS_NOT_EMPTY())),
                 DIV(LABEL('Ingredient Salt:', _for='ingredient_salt')),
                 DIV(INPUT(_name='ingredient_salt', _type='number', requires=IS_NOT_EMPTY())),
                 DIV(INPUT(_type='submit')))
    return iForm

def getRecipeForm():
    rForm = FORM(DIV(LABEL('Recipe Name:', _for='recipe_name')),
                 DIV(INPUT(_name='recipe_name', requires=IS_NOT_EMPTY())),
                 DIV(LABEL('Recipe Instructions:', _for='recipe_instructions')),
                 DIV(TEXTAREA(_name='recipe_instructions', requires=IS_NOT_EMPTY())),
                 DIV(LABEL('Recipe Source:', _for='recipe_source')),
                 DIV(INPUT(_name='recipe_source', requires=IS_NOT_EMPTY())),
                 DIV(LABEL('Recipe Serving:', _for='recipe_serving')),
                 DIV(INPUT(_name='recipe_serving', _type='number', requires=IS_NOT_EMPTY())),
                 DIV(LABEL('Recipe Cooking Time:', _for='recipe_cooktime')),
                 DIV(INPUT(_name='recipe_cooktime', _type='number', requires=IS_NOT_EMPTY())),
                 DIV(LABEL('Recipe Preparation Time:', _for='recipe_preptime')),
                 DIV(INPUT(_name='recipe_preptime', _type='number', requires=IS_NOT_EMPTY())),
                 DIV(LABEL('Recipe Difficulty:', _for='recipe_dif')),
                 DIV(INPUT(_name='recipe_dif', _type='number', requires=IS_NOT_EMPTY())),
                 DIV(INPUT(_type='submit')))
    return rForm

def getIngredientNameList():
    return db(db.ingredients.id > 0).select('name');

def ingredients():
    ingredient = None
    if request.args(0) is not None:
        ingName = request.args(0).replace('_', ' ')
        ingredient = db(db.ingredients.name == ingName).select(db.ingredients.ALL)
    return dict(ingredients=getIngredientNameList(), ing=ingredient)