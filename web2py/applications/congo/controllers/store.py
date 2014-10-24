# -*- coding: utf-8 -*-
# try something like


def index(): 
    return dict(features=db(db.products.id == db.features.product_id).select())


def books():
    if request.args(0) is not None:
        try:
            int(request.args(0))
            return dict(books=db(db.products.id == request.args(0)).select())
        except ValueError:
            pass
    return dict(books=db(db.products.ptype == 'Book').select())


def videos():
    return dict()