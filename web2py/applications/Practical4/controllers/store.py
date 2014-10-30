#@IAPT: Here the controller is returning a dictionary that contains all of the rows from the query.
#@IAPT: Practical 3 - replaced the "books" with "results" to use the subview created.
def books():
    product_id = request.args(0)
    if product_id is not None:
        return dict(results = db((db.products.type == 'Book') & (db.products.id == product_id)).select())
    else:
        return dict(results = db(db.products.type == 'Book').select())

#@IAPT: So here is a version which is MVC based where we are just returning control to the view
#This could be more advanced functionality, like committing changes from the user, doing intermediary
#calculations that the user needs or any number of things in the business logic of the application.
#It just happens that in this case, the controller doesn't have any business logic to execute.
#@IAPT: Practical 3 - replaced the "books" with "results" to use the subview created.
def videos():
    product_id = request.args(0)
    if product_id is not None:
        return dict(results = db((db.products.type == 'Blu-Ray') & (db.products.id == product_id)).select())
    else:
        return dict(results = db(db.products.type == 'Blu-Ray').select())
