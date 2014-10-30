# -*- coding: utf-8 -*-

# @IAPT: This is a JOIN operation using contracted syntax of Web2Py.  See the Web2Py documentation for
#more complex JOIN notation that you might need for your own applications.
def index():
    #@IAPT: We return a dictionary that contains the results of the query - which is actually the two tables
    #matched up in the appropriate join - so we will need to be careful on the return to the view to specify
    #what tables we are looking for our data in.
    return dict(features=db(db.products.id==db.features.product_id).select())

def search():
    #@IAPT Inline form
    form=FORM('Search Products',
              INPUT(_name='search', requires=IS_NOT_EMPTY()),
              INPUT(_type='submit'))
    #@IAPT This is the logic code: If we have a product search accepted, tell people about the search
    if form.accepts(request,session):
        response.flash = 'Performing search for products containing the text: '+request.vars.search+'.'
    #@IAPT If we have an error report it
    elif form.errors:
        response.flash = 'Your form is empty.  Please enter a name of a product to search the store.'
    #@IAPT If we have only just arrived at the page, let people know what they have to do
    else:
        response.flash = 'Please enter a name of a product to search the store.'

    if request.vars.search is not None:
        term="%"+request.vars.search+"%"
        results = db(db.products.name.like(term)).select()
    else:
        results = dict()
    return dict(form=form, results=results)

def addproduct():
    #@IAPT Form containing all of the fields in DIVs to allow for block layout
    addform = FORM(DIV(LABEL('Product Name:', _for='product_name')),
                   DIV(INPUT(_name='product_name', requires=IS_NOT_EMPTY())),
                   DIV(LABEL('Product Price:', _for='product_price')),
                   DIV(INPUT(_name='product_price',requires=IS_NOT_EMPTY())),
                   DIV(LABEL('Product Type', _for='product_type')),
                   DIV(SELECT('Book','Blu-Ray', value='b',_name='product_type')),
                   DIV(LABEL('Product Description', _for='product_description')),
                   DIV(TEXTAREA(_name='product_description', requires=IS_NOT_EMPTY())),
                   DIV(LABEL('Product Publisher', _for='product_publisher')),
                   DIV(INPUT(_name='product_publisher', requires=IS_NOT_EMPTY())),
                   DIV(INPUT(_type='submit')))

    #@IAPT On acceptance we are going to add the item to the database.
    if addform.accepts(request,session):
        db.products.insert(name=request.vars.product_name,price=request.vars.product_price, type=request.vars.product_type,
                           description=request.vars.product_description,publisher=request.vars.product_publisher)
        db.commit
        response.flash = 'New product added to store.'
    elif addform.errors:
        response.flash = 'One or more of your form fields has an error. Please see below for more information'
    else:
        response.flash = 'Please complete the form below to add a new product.'
    return dict(addform=addform)

def updateproduct():
    #@IAPT - this is where we change the type of widget the description gets - this is relatively bad practice, better
    #to do it at time of creation of the database if we are goingto use SQLFORM
    db.products.description.widget = SQLFORM.widgets.text.widget

    #@IAPT retrieve the indiviudal product by getting the arguments of URL
    record = db.products(request.args(0)) or redirect(URL('default', 'noproduct'))
    updateform =SQLFORM(db.products, record, fields=['name', 'price','description','type','publisher'])


    if updateform.accepts(request,session):
        response.flash = 'Product information updated in story inventory.'
    elif updateform.errors:
        response.flash = 'One or more of your form fields has an error. Please see below for more information'
    else:
        response.flash = 'Please complete the form below to add a new product.'
    return dict(updateform=updateform)

def noproduct():
    return dict()