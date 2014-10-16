# -*- coding: utf-8 -*-
# try something like


def index(): 
    return dict(features=db(db.products.id == db.features.product_id).select())


def books():
    return dict(books=db(db.products.ptype == 'Book').select())


def videos():
    return dict()

features = dict( book1={'id': '1', 'name': 'Batman: Arkham Asylum',
'price': '9.00', 'type': 'Book', 'writer': 'Grant Morrison','pages': '216', 'description': 'Some stuff about batman ...' },
                book2={'id': '2', 'name': 'Superman',
'price': '7.00', 'type': 'paperback book', 'writer': 'Some Guy','pages': '159', 'description': 'Some stuff about SUPERMAN ...'})
