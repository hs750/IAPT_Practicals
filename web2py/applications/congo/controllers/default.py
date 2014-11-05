def index():
    return dict()

def search():
    return dict()

def search2():
    form = FORM('Search Products',
                INPUT(_type='search', _name='search', requires=IS_NOT_EMPTY()),
                INPUT(_type='submit'))
    results = None
    if form.accepts(request.post_vars, session) :
        response.flash = "Results displayed"
        results = db(db.products.name.contains(request.post_vars.search)).select()
    elif form.errors:
        response.flash = "There was an error: your form was empty"
    else:
        response.flash = "please enter a search"
    return dict(form=form, results=results)

def addProduct():
    form=FORM('Add Product',
              DIV(LABEL('Name:', _for='Name')),
              DIV(INPUT(_name='Name', requires=IS_NOT_EMPTY())),
              DIV(LABEL('Price', _for='Price')),
              DIV(INPUT(_name='Price', _type='number', requires=IS_NOT_EMPTY(), min=0, step=0.01)),
              DIV(LABEL('Media Type:', _for='Type')),
              DIV(SELECT('Book', 'Blu-Ray', _name='Type')),
              DIV(LABEL('Description', _for='Description')),
              DIV(TEXTAREA(_name='Description', requires=IS_NOT_EMPTY())),
              DIV(LABEL('Publisher:', _for='Publisher')),
              DIV(INPUT(_name='Publisher', requires=IS_NOT_EMPTY())),
              DIV(INPUT(_name='submit', _type='submit')))

    if form.accepts(request.post_vars, session):
        response.flash = "Added to database..."
        db.products.insert(name=request.post_vars.Name,
                           price=request.post_vars.Price,
                           ptype=request.post_vars.Type,
                           description=request.post_vars.Description,
                           publisher=request.post_vars.Publisher)

    elif form.errors:
        response.flash += "Make sure all fields are filled"
    else:
        response.flash = "Please fill out the form..."

    return dict(form=form);

def addProduct2():
    db.products.description.widget = SQLFORM.widgets.text.widget
    if request.args(0) is not None:
        form = SQLFORM(db.products, db.products(request.args(0)), formstyle='bootstrap')
    else:
        form=SQLFORM(db.products, formstyle='bootstrap')

    if form.accepts(request.post_vars, session):
        response.flash = "Added to database..."
        db.products.insert(name=request.post_vars.name,
                           price=request.post_vars.price,
                           ptype=request.post_vars.ptype,
                           description=request.post_vars.description,
                           publisher=request.post_vars.publisher)

    elif form.errors:
        response.flash += "Make sure all fields are filled"
    else:
        response.flash = "Please fill out the form..."

    return dict(form=form);