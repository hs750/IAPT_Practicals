class SQLFORM(FORM):

    """
    SQLFORM is used to map a table (and a current record) into an HTML form.

    Given a Table like db.table

    Generates an insert form::

        SQLFORM(db.table)

    Generates an update form::

        record=db.table[some_id]
        SQLFORM(db.table, record)

    Generates an update with a delete button::

        SQLFORM(db.table, record, deletable=True)

    Args:
        table: `Table` object
        record: either an int if the `id` is an int, or the record fetched
            from the table
        deletable: adds the delete checkbox
        linkto: the URL of a controller/function to access referencedby
            records
        upload: the URL of a controller/function to download an uploaded file
        fields: a list of fields that should be placed in the form,
            default is all.
        labels: a dictionary with labels for each field, keys are the field
            names.
        col3: a dictionary with content for an optional third column
            (right of each field). keys are field names.
        submit_button: text to show in the submit button
        delete_label: text to show next to the delete checkbox
        showid: shows the id of the record
        readonly: doesn't allow for any modification
        comments: show comments (stored in `col3` or in Field definition)
        ignore_rw: overrides readable/writable attributes
        record_id: used to create session key against CSRF
        formstyle: what to use to generate the form layout
        buttons: override buttons as you please (will be also stored in
            `form.custom.submit`)
        separator: character as separator between labels and inputs

    any named optional attribute is passed to the <form> tag
    for example _class, _id, _style, _action, _method, etc.

    """

    # usability improvements proposal by fpp - 4 May 2008 :
    # - correct labels (for points to field id, not field name)
    # - add label for delete checkbox
    # - add translatable label for record ID
    # - add third column to right of fields, populated from the col3 dict

    widgets = Storage(
        string=StringWidget,
        text=TextWidget,
        json=JSONWidget,
        password=PasswordWidget,
        integer=IntegerWidget,
        double=DoubleWidget,
        decimal=DecimalWidget,
        time=TimeWidget,
        date=DateWidget,
        datetime=DatetimeWidget,
        upload=UploadWidget,
        boolean=BooleanWidget,
        blob=None,
        options=OptionsWidget,
        multiple=MultipleOptionsWidget,
        radio=RadioWidget,
        checkboxes=CheckboxesWidget,
        autocomplete=AutocompleteWidget,
        list=ListWidget,
    )

    formstyles = Storage(
        table3cols=formstyle_table3cols,
        table2cols=formstyle_table2cols,
        divs=formstyle_divs,
        ul=formstyle_ul,
        bootstrap=formstyle_bootstrap,
        bootstrap3_stacked=formstyle_bootstrap3_stacked,
        bootstrap3_inline=formstyle_bootstrap3_inline_factory(3),
        inline=formstyle_inline,
        )

    FIELDNAME_REQUEST_DELETE = 'delete_this_record'
    FIELDKEY_DELETE_RECORD = 'delete_record'
    ID_LABEL_SUFFIX = '__label'
    ID_ROW_SUFFIX = '__row'

    def assert_status(self, status, request_vars):
        if not status and self.record and self.errors:
            ### if there are errors in update mode
            # and some errors refers to an already uploaded file
            # delete error if
            # - user not trying to upload a new file
            # - there is existing file and user is not trying to delete it
            # this is because removing the file may not pass validation
            for key in self.errors.keys():
                if key in self.table \
                        and self.table[key].type == 'upload' \
                        and request_vars.get(key, None) in (None, '') \
                        and self.record[key] \
                        and not key + UploadWidget.ID_DELETE_SUFFIX in request_vars:
                    del self.errors[key]
            if not self.errors:
                status = True
        return status

    def __init__(
        self,
        table,
        record=None,
        deletable=False,
        linkto=None,
        upload=None,
        fields=None,
        labels=None,
        col3={},
        submit_button='Submit',
        delete_label='Check to delete',
        showid=True,
        readonly=False,
        comments=True,
        keepopts=[],
        ignore_rw=False,
        record_id=None,
        formstyle=None,
        buttons=['submit'],
        separator=None,
        extra_fields=None,
        **attributes
    ):
        T = current.T

        self.ignore_rw = ignore_rw
        self.formstyle = formstyle or current.response.formstyle
        self.readonly = readonly
        # Default dbio setting
        self.detect_record_change = None

        nbsp = XML('&nbsp;')  # Firefox2 does not display fields with blanks
        FORM.__init__(self, *[], **attributes)
        ofields = fields
        keyed = hasattr(table, '_primarykey')  # for backward compatibility

        # if no fields are provided, build it from the provided table
        # will only use writable or readable fields, unless forced to ignore
        if fields is None:
            fields = [f.name for f in table if
                      (ignore_rw or f.writable or f.readable) and
                      (readonly or not f.compute)]
        self.fields = fields

        # make sure we have an id
        if self.fields[0] != table.fields[0] and \
                isinstance(table, Table) and not keyed:
            self.fields.insert(0, table.fields[0])

        self.table = table

        # try to retrieve the indicated record using its id
        # otherwise ignore it
        if record and isinstance(record, (int, long, str, unicode)):
            if not str(record).isdigit():
                raise HTTP(404, "Object not found")
            record = table._db(table._id == record).select().first()
            if not record:
                raise HTTP(404, "Object not found")
        self.record = record

        self.record_id = record_id
        if keyed:
            self.record_id = dict([(k, record and str(record[k]) or None)
                                   for k in table._primarykey])
        self.field_parent = {}
        xfields = []
        self.fields = fields
        self.custom = Storage()
        self.custom.dspval = Storage()
        self.custom.inpval = Storage()
        self.custom.label = Storage()
        self.custom.comment = Storage()
        self.custom.widget = Storage()
        self.custom.linkto = Storage()

        # default id field name
        if not keyed:
            self.id_field_name = table._id.name
        else:
            self.id_field_name = table._primarykey[0]  # only works if one key

        sep = separator or current.response.form_label_separator

        extra_fields = extra_fields or []
        self.extra_fields = {}
        for extra_field in extra_fields:
            self.fields.append(extra_field.name)
            self.extra_fields[extra_field.name] = extra_field
            extra_field.db = table._db
            extra_field.table = table
            extra_field.tablename = table._tablename
            if extra_field.requires == DEFAULT:
                extra_field.requires = sqlhtml_validators(extra_field)

        for fieldname in self.fields:
            if fieldname.find('.') >= 0:
                continue

            field = (self.table[fieldname] if fieldname in self.table.fields 
                     else self.extra_fields[fieldname])
            comment = None

            if comments:
                comment = col3.get(fieldname, field.comment)
            if comment is None:
                comment = ''
            self.custom.comment[fieldname] = comment

            if not labels is None and fieldname in labels:
                label = labels[fieldname]
            else:
                label = field.label
            self.custom.label[fieldname] = label

            field_id = '%s_%s' % (table._tablename, fieldname)

            label = LABEL(label, label and sep, _for=field_id,
                          _id=field_id + SQLFORM.ID_LABEL_SUFFIX)

            row_id = field_id + SQLFORM.ID_ROW_SUFFIX
            if field.type == 'id':
                self.custom.dspval.id = nbsp
                self.custom.inpval.id = ''
                widget = ''

                # store the id field name (for legacy databases)
                self.id_field_name = field.name

                if record:
                    if showid and field.name in record and field.readable:
                        v = record[field.name]
                        widget = SPAN(v, _id=field_id)
                        self.custom.dspval.id = str(v)
                        xfields.append((row_id, label, widget, comment))
                    self.record_id = str(record[field.name])
                self.custom.widget.id = widget
                continue

            if readonly and not ignore_rw and not field.readable:
                continue

            if record:
                default = record[fieldname]
            else:
                default = field.default
                if isinstance(default, CALLABLETYPES):
                    default = default()
            cond = readonly or \
                (not ignore_rw and not field.writable and field.readable)

            if default is not None and not cond:                
                default = field.formatter(default)

            dspval = default
            inpval = default

            if cond:

                # ## if field.re                field.requires = sqlhtml_validators(field)                field.requires = sqlhtml_validators(field)present is available else
                # ## ignore blob and preview uploaded images
                # ## format everything else

                if field.represent:
                    inp = represent(field, default, record)
                elif field.type in ['blob']:
                    continue
                elif field.type == 'upload':
                    inp = UploadWidget.represent(field, default, upload)
                elif field.type == 'boolean':
                    inp = self.widgets.boolean.widget(
                        field, default, _disabled=True)
                else:
                    inp = field.formatter(default)
            elif field.type == 'upload':
                if field.widget:
                    inp = field.widget(field, default, upload)
                else:
                    inp = self.widgets.upload.widget(field, default, upload)
            elif field.widget:
                inp = field.widget(field, default)
            elif field.type == 'boolean':
                inp = self.widgets.boolean.widget(field, default)
                if default:
                    inpval = 'checked'
                else:
                    inpval = ''
            elif OptionsWidget.has_options(field):
                if not field.requires.multiple:
                    inp = self.widgets.options.widget(field, default)
                else:
                    inp = self.widgets.multiple.widget(field, default)
                if fieldname in keepopts:
                    inpval = TAG[''](*inp.components)
            elif field.type.startswith('list:'):
                inp = self.widgets.list.widget(field, default)
            elif field.type == 'text':
                inp = self.widgets.text.widget(field, default)
            elif field.type == 'password':
                inp = self.widgets.password.widget(field, default)
                if self.record:
                    dspval = DEFAULT_PASSWORD_DISPLAY
                else:
                    dspval = ''
            elif field.type == 'blob':
                continue
            else:
                field_type = widget_class.match(str(field.type)).group()
                field_type = field_type in self.widgets and field_type or 'string'
                inp = self.widgets[field_type].widget(field, default)

            xfields.append((row_id, label, inp, comment))
            self.custom.dspval[fieldname] = dspval if (dspval is not None) else nbsp
            self.custom.inpval[fieldname] = inpval if not inpval is None else ''
            self.custom.widget[fieldname] = inp

        # if a record is provided and found, as is linkto
        # build a link
        if record and linkto:
            db = linkto.split('/')[-1]
            for rfld in table._referenced_by:
                if keyed:
                    query = urllib.quote('%s.%s==%s' % (
                        db, rfld, record[rfld.type[10:].split('.')[1]]))
                else:
                    query = urllib.quote(
                        '%s.%s==%s' % (db, rfld, record[self.id_field_name]))
                lname = olname = '%s.%s' % (rfld.tablename, rfld.name)
                if ofields and not olname in ofields:
                    continue
                if labels and lname in labels:
                    lname = labels[lname]
                widget = A(lname,
                           _class='reference',
                           _href='%s/%s?query=%s' % (linkto, rfld.tablename, query))
                xfields.append(
                    (olname.replace('.', '__') + SQLFORM.ID_ROW_SUFFIX,
                     '', widget, col3.get(olname, '')))
                self.custom.linkto[olname.replace('.', '__')] = widget
#                 </block>

        # when deletable, add delete? checkbox
        self.custom.delete = self.custom.deletable = ''
        if record and deletable:
            #add secondary css class for cascade delete warning
            css = 'delete'
            for f in self.table.fields:
                on_del = self.table[f].ondelete
                if isinstance(on_del, str) and 'cascade' in on_del.lower():
                    css += ' cascade_delete'
                    break
            widget = INPUT(_type='checkbox',
                           _class=css,
                           _id=self.FIELDKEY_DELETE_RECORD,
                           _name=self.FIELDNAME_REQUEST_DELETE,
                           )
            xfields.append(
                (self.FIELDKEY_DELETE_RECORD + SQLFORM.ID_ROW_SUFFIX,
                 LABEL(
                        T(delete_label), sep,
                        _for=self.FIELDKEY_DELETE_RECORD,
                        _id=self.FIELDKEY_DELETE_RECORD + \
                            SQLFORM.ID_LABEL_SUFFIX),
                 widget,
                 col3.get(self.FIELDKEY_DELETE_RECORD, '')))
            self.custom.delete = self.custom.deletable = widget


        # when writable, add submit button
        self.custom.submit = ''
        if not readonly:
            if 'submit' in buttons:
                widget = self.custom.submit = INPUT(_type='submit',
                                                    _value=T(submit_button))
            elif buttons:
                widget = self.custom.submit = DIV(*buttons)
            if self.custom.submit:
                xfields.append(('submit_record' + SQLFORM.ID_ROW_SUFFIX,
                                '', widget, col3.get('submit_button', '')))

        # if a record is provided and found
        # make sure it's id is stored in the form
        if record:
            if not self['hidden']:
                self['hidden'] = {}
            if not keyed:
                self['hidden']['id'] = record[table._id.name]

        (begin, end) = self._xml()
        self.custom.begin = XML("<%s %s>" % (self.tag, begin))
        self.custom.end = XML("%s</%s>" % (end, self.tag))
        table = self.createform(xfields)
        self.components = [table]


    def createform(self, xfields):
        formstyle = self.formstyle
        if isinstance(formstyle, basestring):
            if formstyle in SQLFORM.formstyles:
                formstyle = SQLFORM.formstyles[formstyle]
            else:
                raise RuntimeError('formstyle not found')

        if callable(formstyle):
            try:
                table = formstyle(self, xfields)
                for id, a, b, c in xfields:
                    self.field_parent[id] = getattr(b, 'parent', None) \
                        if isinstance(b, XmlComponent) else None
            except TypeError:
                # backward compatibility, 4 argument function is the old style
                table = TABLE()
                for id, a, b, c in xfields:
                    newrows = formstyle(id, a, b, c)
                    self.field_parent[id] = getattr(b, 'parent', None) \
                        if isinstance(b, XmlComponent) else None
                    if type(newrows).__name__ != "tuple":
                        newrows = [newrows]
                    for newrow in newrows:
                        table.append(newrow)
        else:
            raise RuntimeError('formstyle not supported')
        return table

    def accepts(
        self,
        request_vars,
        session=None,
        formname='%(tablename)s/%(record_id)s',
        keepvalues=None,
        onvalidation=None,
        dbio=True,
        hideerror=False,
        detect_record_change=False,
        **kwargs
    ):

        """
        Similar to `FORM.accepts` but also does insert, update or delete in DAL.
        If detect_record_change is `True` than:

          - `form.record_changed = False` (record is properly validated/submitted)
          - `form.record_changed = True` (record cannot be submitted because changed)

        If detect_record_change == False than:

          - `form.record_changed = None`
        """

        if keepvalues is None:
            keepvalues = True if self.record else False

        if self.readonly:
            return False

        if request_vars.__class__.__name__ == 'Request':
            request_vars = request_vars.post_vars

        keyed = hasattr(self.table, '_primarykey')

        # implement logic to detect whether record exist but has been modified
        # server side
        self.record_changed = None
        self.detect_record_change = detect_record_change
        if self.detect_record_change:
            if self.record:
                self.record_changed = False
                serialized = '|'.join(
                    str(self.record[k]) for k in self.table.fields())
                self.record_hash = md5_hash(serialized)

        # logic to deal with record_id for keyed tables
        if self.record:
            if keyed:
                formname_id = '.'.join(str(self.record[k])
                                       for k in self.table._primarykey
                                       if hasattr(self.record, k))
                record_id = dict((k, request_vars.get(k, None))
                                 for k in self.table._primarykey)
            else:
                (formname_id, record_id) = (self.record[self.id_field_name],
                                            request_vars.get('id', None))
            keepvalues = True
        else:
            if keyed:
                formname_id = 'create'
                record_id = dict([(k, None) for k in self.table._primarykey])
            else:
                (formname_id, record_id) = ('create', None)

        if not keyed and isinstance(record_id, (list, tuple)):
            record_id = record_id[0]

        if formname:
            formname = formname % dict(tablename=self.table._tablename,
                                       record_id=formname_id)

        # ## THIS IS FOR UNIQUE RECORDS, read IS_NOT_IN_DB

        for fieldname in self.fields:
            field = (self.table[fieldname] if fieldname in self.table.fields
                     else self.extra_fields[fieldname])
            requires = field.requires or []
            if not isinstance(requires, (list, tuple)):
                requires = [requires]
            [item.set_self_id(self.record_id) for item in requires
             if hasattr(item, 'set_self_id') and self.record_id]

        # ## END

        fields = {}
        for key in self.vars:
            fields[key] = self.vars[key]

        ret = FORM.accepts(
            self,
            request_vars,
            session,
            formname,
            keepvalues,
            onvalidation,
            hideerror=hideerror,
            **kwargs
        )

        self.deleted = \
            request_vars.get(self.FIELDNAME_REQUEST_DELETE, False)

        self.custom.end = TAG[''](self.hidden_fields(), self.custom.end)

        auch = record_id and self.errors and self.deleted

        if self.record_changed and self.detect_record_change:
            message_onchange = \
                kwargs.setdefault("message_onchange",
                    current.T("A record change was detected. " +
                            "Consecutive update self-submissions " +
                            "are not allowed. Try re-submitting or " +
                            "refreshing the form page."))
            if message_onchange is not None:
                current.response.flash = message_onchange
            return ret
        elif (not ret) and (not auch):
            # auch is true when user tries to delete a record
            # that does not pass validation, yet it should be deleted
            for fieldname in self.fields:

                field = (self.table[fieldname] 
                         if fieldname in self.table.fields
                         else self.extra_fields[fieldname])
                ### this is a workaround! widgets should always have default not None!
                if not field.widget and field.type.startswith('list:') and \
                        not OptionsWidget.has_options(field):
                    field.widget = self.widgets.list.widget
                if field.widget and fieldname in request_vars:
                    if fieldname in self.request_vars:
                        value = self.request_vars[fieldname]
                    elif self.record:
                        value = self.record[fieldname]
                    else:
                        value = field.default
                    row_id = '%s_%s%s' % (
                        self.table, fieldname, SQLFORM.ID_ROW_SUFFIX)
                    widget = field.widget(field, value)
                    parent = self.field_parent[row_id]
                    if parent:
                        parent.components = [widget]
                        if self.errors.get(fieldname):
                            parent._traverse(False, hideerror)
                    self.custom.widget[fieldname] = widget
            self.accepted = ret
            return ret

        if record_id and str(record_id) != str(self.record_id):
            raise SyntaxError('user is tampering with form\'s record_id: '
                              '%s != %s' % (record_id, self.record_id))

        if record_id and dbio and not keyed:
            self.vars.id = self.record[self.id_field_name]

        if self.deleted and self.custom.deletable:
            if dbio:
                if keyed:
                    qry = reduce(lambda x, y: x & y,
                                 [self.table[k] == record_id[k]
                                  for k in self.table._primarykey])
                else:
                    qry = self.table._id == self.record[self.id_field_name]
                self.table._db(qry).delete()
            self.errors.clear()
            for component in self.elements('input, select, textarea'):
                component['_disabled'] = True
            self.accepted = True
            return True

        for fieldname in self.fields:
            if not fieldname in self.table.fields:
                continue

            if not self.ignore_rw and not self.table[fieldname].writable:
                ### this happens because FORM has no knowledge of writable
                ### and thinks that a missing boolean field is a None
                if self.table[fieldname].type == 'boolean' and \
                        self.vars.get(fieldname, True) is None:
                    del self.vars[fieldname]
                continue

            field = self.table[fieldname]
            if field.type == 'id':
                continue
            if field.type == 'boolean':
                if self.vars.get(fieldname, False):
                    self.vars[fieldname] = fields[fieldname] = True
                else:
                    self.vars[fieldname] = fields[fieldname] = False
            elif field.type == 'password' and self.record\
                and request_vars.get(fieldname, None) == DEFAULT_PASSWORD_DISPLAY:
                continue  # do not update if password was not changed
            elif field.type == 'upload':
                f = self.vars[fieldname]
                fd = '%s__delete' % fieldname
                if f == '' or f is None:
                    if self.vars.get(fd, False):
                        f = self.table[fieldname].default or ''
                        fields[fieldname] = f
                    elif self.record:
                        if self.record[fieldname]:
                            fields[fieldname] = self.record[fieldname]
                        else:
                            f = self.table[fieldname].default or ''
                            fields[fieldname] = f
                    else:
                        f = self.table[fieldname].default or ''
                        fields[fieldname] = f
                    self.vars[fieldname] = fields[fieldname]
                    if not f:
                        continue
                    else:
                        f = os.path.join(
                            current.request.folder,
                            os.path.normpath(f))
                        source_file = open(f, 'rb')
                        original_filename = os.path.split(f)[1]
                elif hasattr(f, 'file'):
                    (source_file, original_filename) = (f.file, f.filename)
                elif isinstance(f, (str, unicode)):
                    ### do not know why this happens, it should not
                    (source_file, original_filename) = \
                        (cStringIO.StringIO(f), 'file.txt')
                else:
                    # this should never happen, why does it happen?
                    #print 'f=',repr(f)
                    continue
                newfilename = field.store(source_file, original_filename,
                                          field.uploadfolder)
                # this line was for backward compatibility but problematic
                # self.vars['%s_newfilename' % fieldname] = newfilename
                fields[fieldname] = newfilename
                if isinstance(field.uploadfield, str):
                    fields[field.uploadfield] = source_file.read()
                # proposed by Hamdy (accept?) do we need fields at this point?
                self.vars[fieldname] = fields[fieldname]
                continue
            elif fieldname in self.vars:
                fields[fieldname] = self.vars[fieldname]
            elif field.default is None and field.type != 'blob':
                self.errors[fieldname] = 'no data'
                self.accepted = False
                return False
            value = fields.get(fieldname, None)
            if field.type == 'list:string':
                if not isinstance(value, (tuple, list)):
                    fields[fieldname] = value and [value] or []
            elif isinstance(field.type, str) and field.type.startswith('list:'):
                if not isinstance(value, list):
                    fields[fieldname] = [safe_int(
                        x) for x in (value and [value] or [])]
            elif field.type == 'integer':
                if not value is None:
                    fields[fieldname] = safe_int(value)
            elif field.type.startswith('reference'):
                ## Avoid "constraint violation" exception when you have a
                ## optional reference field without the dropdown in form. I.e.,
                ## a field with code to be typed, in a data-entry form.
                ##
                ## When your reference field doesn't have IS_EMPTY_OR()
                ## validator, "value" will come here as a string. So,
                ## safe_int() will return 0. In this case, insert will raise
                ## the constraint violation because there's no id=0 in
                ## referenced table.
                if isinstance(self.table, Table) and not keyed:
                    if not value:
                        fields[fieldname] = None
                    else:
                        fields[fieldname] = safe_int(value)
            elif field.type == 'double':
                if not value is None:
                    fields[fieldname] = safe_float(value)

        for fieldname in self.vars:
            if fieldname != 'id' and fieldname in self.table.fields\
                and not fieldname in fields and not fieldname\
                    in request_vars:
                fields[fieldname] = self.vars[fieldname]

        if dbio:
            for fieldname in fields:
                if fieldname in self.extra_fields:
                    del fields[fieldname]
            if 'delete_this_record' in fields:
                # this should never happen but seems to happen to some
                del fields['delete_this_record']
            for field in self.table:
                if not field.name in fields and field.writable is False \
                        and field.update is None and field.compute is None:
                    if record_id and self.record:
                        fields[field.name] = self.record[field.name]
                    elif not self.table[field.name].default is None:
                        fields[field.name] = self.table[field.name].default
            if keyed:
                if reduce(lambda x, y: x and y, record_id.values()):  # if record_id
                    if fields:
                        qry = reduce(lambda x, y: x & y,
                                     [self.table[k] == self.record[k] for k in self.table._primarykey])
                        self.table._db(qry).update(**fields)
                else:
                    pk = self.table.insert(**fields)
                    if pk:
                        self.vars.update(pk)
                    else:
                        ret = False
            else:
                if record_id:
                    self.vars.id = self.record[self.id_field_name]
                    if fields:
                        self.table._db(self.table._id == self.record[
                                       self.id_field_name]).update(**fields)
                else:
                    self.vars.id = self.table.insert(**fields)
        self.accepted = ret
        return ret

    AUTOTYPES = {
        type(''): ('string', None),
        type(True): ('boolean', None),
        type(1): ('integer', IS_INT_IN_RANGE(-1e12, +1e12)),
        type(1.0): ('double', IS_FLOAT_IN_RANGE()),
        type([]): ('list:string', None),
        type(datetime.date.today()): ('date', IS_DATE()),
        type(datetime.datetime.today()): ('datetime', IS_DATETIME())
    }

    @staticmethod
    def dictform(dictionary, **kwargs):
        fields = []
        for key, value in sorted(dictionary.items()):
            t, requires = SQLFORM.AUTOTYPES.get(type(value), (None, None))
            if t:
                fields.append(Field(key, t, requires=requires,
                                    default=value))
        return SQLFORM.factory(*fields, **kwargs)

    @staticmethod
    def smartdictform(session, name, filename=None, query=None, **kwargs):
        if query:
            session[name] = query.db(query).select().first().as_dict()
        elif os.path.exists(filename):
            env = {'datetime': datetime}
            session[name] = eval(open(filename).read(), {}, env)
        form = SQLFORM.dictform(session[name])
        if form.process().accepted:
            session[name].update(form.vars)
            if query:
                query.db(query).update(**form.vars)
            else:
                open(filename, 'w').write(repr(session[name]))
        return form

    @staticmethod
    def factory(*fields, **attributes):
        """
        Generates a SQLFORM for the given fields.

        Internally will build a non-database based data model
        to hold the fields.
        """
        # Define a table name, this way it can be logical to our CSS.
        # And if you switch from using SQLFORM to SQLFORM.factory
        # your same css definitions will still apply.

        table_name = attributes.get('table_name', 'no_table')

        # So it won't interfere with SQLDB.define_table
        if 'table_name' in attributes:
            del attributes['table_name']

        return SQLFORM(DAL(None).define_table(table_name, *fields),
                       **attributes)

    @staticmethod
    def build_query(fields, keywords):
        request = current.request
        if isinstance(keywords, (tuple, list)):
            keywords = keywords[0]
            request.vars.keywords = keywords
        key = keywords.strip()
        if key and not ' ' in key and not '"' in key and not "'" in key:
            SEARCHABLE_TYPES = ('string', 'text', 'list:string')
            parts = [field.contains(
                key) for field in fields if field.type in SEARCHABLE_TYPES]

            # from https://groups.google.com/forum/#!topic/web2py/hKe6lI25Bv4
            # needs testing...
            #words = key.split(' ') if key else []
            #filters = []
            #for field in fields:
            #    if field.type in SEARCHABLE_TYPES:
            #        all_words_filters = []
            #        for word in words:
            #        all_words_filters.append(field.contains(word))
            #        filters.append(reduce(lambda a, b: (a & b), all_words_filters))
            #parts = filters

        else:
            parts = None
        if parts:
            return reduce(lambda a, b: a | b, parts)
        else:
            return smart_query(fields, key)

    @staticmethod
    def search_menu(fields,
                    search_options=None,
                    prefix='w2p'
                    ):
        T = current.T
        panel_id='%s_query_panel' % prefix
        fields_id='%s_query_fields' % prefix
        keywords_id='%s_keywords' % prefix
        field_id='%s_field' % prefix
        value_id='%s_value' % prefix
        search_options = search_options or {
            'string': ['=', '!=', '<', '>', '<=', '>=', 'starts with', 'contains', 'in', 'not in'],
            'text': ['=', '!=', '<', '>', '<=', '>=', 'starts with', 'contains', 'in', 'not in'],
            'date': ['=', '!=', '<', '>', '<=', '>='],
            'time': ['=', '!=', '<', '>', '<=', '>='],
            'datetime': ['=', '!=', '<', '>', '<=', '>='],
            'integer': ['=', '!=', '<', '>', '<=', '>=', 'in', 'not in'],
            'double': ['=', '!=', '<', '>', '<=', '>='],
            'id': ['=', '!=', '<', '>', '<=', '>=', 'in', 'not in'],
            'reference': ['=', '!='],
            'boolean': ['=', '!=']}
        if fields[0]._db._adapter.dbengine == 'google:datastore':
            search_options['string'] = ['=', '!=', '<', '>', '<=', '>=']
            search_options['text'] = ['=', '!=', '<', '>', '<=', '>=']
            search_options['list:string'] = ['contains']
            search_options['list:integer'] = ['contains']
            search_options['list:reference'] = ['contains']
        criteria = []
        selectfields = []
        for field in fields:
            name = str(field).replace('.', '-')
            # treat ftype 'decimal' as 'double'
            # (this fixes problems but needs refactoring!
            if isinstance(field.type, SQLCustomType):
                            ftype = field.type.type.split(' ')[0]
            else:
                ftype = field.type.split(' ')[0]
            if ftype.startswith('decimal'): ftype = 'double'
            elif ftype == 'bigint': ftype = 'integer'
            elif ftype.startswith('big-'): ftype = ftype[4:]
            # end
            options = search_options.get(ftype, None)
            if options:
                label = isinstance(
                    field.label, str) and T(field.label) or field.label
                selectfields.append(OPTION(label, _value=str(field)))
                operators = SELECT(*[OPTION(T(option), _value=option) for option in options],_class='form-control')
                _id = "%s_%s" % (value_id, name)
                if field.type == 'boolean':
                    value_input = SQLFORM.widgets.boolean.widget(field, field.default, _id=_id,_class='form-control')
                elif field.type == 'double':
                    value_input = SQLFORM.widgets.double.widget(field, field.default, _id=_id,_class='form-control')
                elif field.type == 'time':
                    value_input = SQLFORM.widgets.time.widget(field, field.default, _id=_id,_class='form-control')
                elif field.type == 'date':
                    iso_format = {'_data-w2p_date_format' : '%Y-%m-%d'}
                    value_input = SQLFORM.widgets.date.widget(field, field.default, _id=_id,_class='form-control', **iso_format)
                elif field.type == 'datetime':
                    iso_format = {'_data-w2p_datetime_format' : '%Y-%m-%d %H:%M:%S'}
                    value_input = SQLFORM.widgets.datetime.widget(field, field.default, _id=_id,_class='form-control', **iso_format)
                elif (field.type.startswith('reference ') or
                      field.type.startswith('list:reference ')) and \
                      hasattr(field.requires, 'options'):
                    value_input = SELECT(
                        *[OPTION(v, _value=k)
                          for k, v in field.requires.options()],
                         _class='form-control',
                         **dict(_id=_id))
                elif field.type == 'integer' or \
                        field.type.startswith('reference ') or \
                        field.type.startswith('list:integer') or \
                        field.type.startswith('list:reference '):
                    value_input = SQLFORM.widgets.integer.widget(field, field.default, _id=_id,_class='form-control')
                else:
                    value_input = INPUT(
                        _type='text', _id=_id, 
                        _class=(field.type or '')+' form-control')

                new_button = INPUT(
                    _type="button", _value=T('New Search'), _class="btn btn-default", _title=T('Start building a new search'),
                    _onclick="%s_build_query('new','%s')" % (prefix, field))
                and_button = INPUT(
                    _type="button", _value=T('+ And'), _class="btn btn-default", _title=T('Add this to the search as an AND term'),
                    _onclick="%s_build_query('and','%s')" % (prefix, field))
                or_button = INPUT(
                    _type="button", _value=T('+ Or'), _class="btn btn-default", _title=T('Add this to the search as an OR term'),
                    _onclick="%s_build_query('or','%s')" % (prefix, field))
                close_button = INPUT(
                    _type="button", _value=T('Close'), _class="btn btn-default",
                    _onclick="jQuery('#%s').slideUp()" % panel_id)

                criteria.append(DIV(
                    operators, value_input, new_button,
                    and_button, or_button, close_button,
                    _id='%s_%s' % (field_id, name),
                        _class='w2p_query_row',
                        _style='display:none'))

        criteria.insert(0, SELECT(
                _id=fields_id,
                _onchange="jQuery('.w2p_query_row').hide();jQuery('#%s_'+jQuery('#%s').val().replace('.','-')).show();" % (field_id, fields_id),
                _style='float:left',_class='form-control',
                *selectfields))

        fadd = SCRIPT("""
        jQuery('#%(fields_id)s input,#%(fields_id)s select').css(
            'width','auto');
        jQuery(function(){web2py_ajax_fields('#%(fields_id)s');});
        function %(prefix)s_build_query(aggregator,a) {
          var b=a.replace('.','-');
          var option = jQuery('#%(field_id)s_'+b+' select').val();
          var value = jQuery('#%(value_id)s_'+b).val().replace('"','\\\\"');
          var s=a+' '+option+' "'+value+'"';
          var k=jQuery('#%(keywords_id)s');
          var v=k.val();
          if(aggregator=='new') k.val(s); else k.val((v?(v+' '+ aggregator +' '):'')+s);
        }
        """ % dict(
                   prefix=prefix, fields_id=fields_id, keywords_id=keywords_id,
                   field_id=field_id, value_id=value_id
                   )
        )
        return CAT(
            DIV(_id=panel_id, _style="display:none;", *criteria), fadd)

    @staticmethod
    def grid(query,
             fields=None,
             field_id=None,
             left=None,
             headers={},
             orderby=None,
             groupby=None,
             searchable=True,
             sortable=True,
             paginate=20,
             deletable=True,
             editable=True,
             details=True,
             selectable=None,
             create=True,
             csv=True,
             links=None,
             links_in_grid=True,
             upload='<default>',
             args=[],
             user_signature=True,
             maxtextlengths={},
             maxtextlength=20,
             onvalidation=None,
             onfailure=None,
             oncreate=None,
             onupdate=None,
             ondelete=None,
             sorter_icons=(XML('&#x25B2;'), XML('&#x25BC;')),
             ui = 'web2py',
             showbuttontext=True,
             _class="web2py_grid",
             formname='web2py_grid',
             search_widget='default',
             advanced_search=True,
             ignore_rw = False,
             formstyle = None,
             exportclasses = None,
             formargs={},
             createargs={},
             editargs={},
             viewargs={},
             selectable_submit_button='Submit',
             buttons_placement = 'right',
             links_placement = 'right',
             noconfirm=False,
             cache_count=None,
             client_side_delete=False,
             ignore_common_filters=None):

        formstyle = formstyle or current.response.formstyle

        # jQuery UI ThemeRoller classes (empty if ui is disabled)
        if ui == 'jquery-ui':
            ui = dict(widget='ui-widget',
                      header='ui-widget-header',
                      content='ui-widget-content',
                      default='ui-state-default',
                      cornerall='ui-corner-all',
                      cornertop='ui-corner-top',
                      cornerbottom='ui-corner-bottom',
                      button='ui-button-text-icon-primary',
                      buttontext='ui-button-text',
                      buttonadd='ui-icon ui-icon-plusthick',
                      buttonback='ui-icon ui-icon-arrowreturnthick-1-w',
                      buttonexport='ui-icon ui-icon-transferthick-e-w',
                      buttondelete='ui-icon ui-icon-trash',
                      buttonedit='ui-icon ui-icon-pencil',
                      buttontable='ui-icon ui-icon-triangle-1-e',
                      buttonview='ui-icon ui-icon-zoomin',
                      )
        elif ui == 'web2py':
            ui = dict(widget='',
                      header='',
                      content='',
                      default='',
                      cornerall='',
                      cornertop='',
                      cornerbottom='',
                      button='button btn btn-default',
                      buttontext='buttontext button',
                      buttonadd='icon plus icon-plus glyphicon glyphicon-plus',
                      buttonback='icon leftarrow icon-arrow-left glyphicon glyphicon-arrow-left',
                      buttonexport='icon downarrow icon-download glyphicon glyphicon-download',
                      buttondelete='icon trash icon-trash glyphicon glyphicon-trash',
                      buttonedit='icon pen icon-pencil glyphicon glyphicon-arrow-pencil',
                      buttontable='icon rightarrow icon-arrow-right glyphicon glyphicon-arrow-right',
                      buttonview='icon magnifier icon-zoom-in glyphicon glyphicon-arrow-zoom-in',
                      )
        elif not isinstance(ui, dict):
            raise RuntimeError('SQLFORM.grid ui argument must be a dictionary')

        db = query._db
        T = current.T
        request = current.request
        session = current.session
        response = current.response
        logged = session.auth and session.auth.user
        wenabled = (not user_signature or logged) and not groupby
        create = wenabled and create
        editable = wenabled and editable
        deletable = wenabled and deletable
        details = details and not groupby
        rows = None

        def fetch_count(dbset):
            ##FIXME for google:datastore cache_count is ignored
            ## if it's not an integer
            if cache_count is None or isinstance(cache_count, tuple):
                if groupby:
                    c = 'count(*)'
                    nrows = db.executesql(
                        'select count(*) from (%s) _tmp;' %
                        dbset._select(c, left=left, cacheable=True,
                                      groupby=groupby,
                                      cache=cache_count)[:-1])[0][0]
                elif left:
                    c = 'count(*)'
                    nrows = dbset.select(c, left=left, cacheable=True, cache=cache_count).first()[c]
                elif dbset._db._adapter.dbengine=='google:datastore':
                    #if we don't set a limit, this can timeout for a large table
                    nrows = dbset.db._adapter.count(dbset.query, limit=1000)
                else:
                    nrows = dbset.count(cache=cache_count)
            elif isinstance(cache_count, (int, long)):
                    nrows = cache_count
            elif callable(cache_count):
                nrows = cache_count(dbset, request.vars)
            else:
                nrows = 0
            return nrows

        def url(**b):
            b['args'] = args + b.get('args', [])
            localvars = request.get_vars.copy()
            localvars.update(b.get('vars', {}))
            b['vars'] = localvars
            b['hash_vars'] = False
            b['user_signature'] = user_signature
            return URL(**b)

        def url2(**b):
            b['args'] = request.args + b.get('args', [])
            localvars = request.get_vars.copy()
            localvars.update(b.get('vars', {}))
            b['vars'] = localvars
            b['hash_vars'] = False
            b['user_signature'] = user_signature
            return URL(**b)

        referrer = session.get('_web2py_grid_referrer_' + formname, url())
        # if not user_signature every action is accessible
        # else forbid access unless
        # - url is based url
        # - url has valid signature (vars are not signed, only path_info)
        # = url does not contain 'create','delete','edit' (readonly)
        if user_signature:
            if not (
                '/'.join(str(a) for a in args) == '/'.join(request.args) or
                URL.verify(request, user_signature=user_signature,
                           hash_vars=False) or
                (request.args(len(args))=='view' and not logged)):
                session.flash = T('not authorized')
                redirect(referrer)

        def gridbutton(buttonclass='buttonadd', buttontext=T('Add'),
                       buttonurl=url(args=[]), callback=None,
                       delete=None, trap=True, noconfirm=None, title=None):
            if showbuttontext:
                return A(SPAN(_class=ui.get(buttonclass)),
                         SPAN(T(buttontext), _title=title or T(buttontext),
                              _class=ui.get('buttontext')),
                         _href=buttonurl,
                         callback=callback,
                         delete=delete,
                         noconfirm=noconfirm,
                         _class=ui.get('button'),
                         cid=request.cid)
            else:
                return A(SPAN(_class=ui.get(buttonclass)),
                         _href=buttonurl,
                         callback=callback,
                         delete=delete,
                         noconfirm=noconfirm,
                         _title=title or T(buttontext),
                         _class=ui.get('button'),
                         cid=request.cid)

        dbset = db(query, ignore_common_filters=ignore_common_filters)
        tablenames = db._adapter.tables(dbset.query)
        if left is not None:
            if not isinstance(left, (list, tuple)):
                left = [left]
            for join in left:
                tablenames += db._adapter.tables(join)
        tables = [db[tablename] for tablename in tablenames]
        if fields:
            #add missing tablename to virtual fields
            for table in tables:
                for k, f in table.iteritems():
                    if isinstance(f, Field.Virtual):
                        f.tablename = table._tablename
            columns = [f for f in fields if f.tablename in tablenames]
        else:
            fields = []
            columns = []
            filter1 = lambda f:isinstance(f, Field)
            filter2 = lambda f:isinstance(f, Field) and f.readable
            for table in tables:
                fields += filter(filter1, table)
                columns += filter(filter2, table)
                for k, f in table.iteritems():
                    if not k.startswith('_'):
                        if isinstance(f, Field.Virtual) and f.readable:
                            f.tablename = table._tablename
                            fields.append(f)
                            columns.append(f)
        if not field_id:
            if groupby is None:
                field_id = tables[0]._id
            elif groupby and isinstance(groupby, Field):
                field_id = groupby #take the field passed as groupby
            elif groupby and isinstance(groupby, Expression):
                field_id = groupby.first #take the first groupby field
                while not(isinstance(field_id, Field)): # Navigate to the first Field of the expression
                    field_id = field_id.first
        table = field_id.table
        tablename = table._tablename
        if not any(str(f) == str(field_id) for f in fields):
            fields = [f for f in fields]+[field_id]
        if upload == '<default>':
            upload = lambda filename: url(args=['download', filename])
            if request.args(-2) == 'download':
                stream = response.download(request, db)
                raise HTTP(200, stream, **response.headers)

        def buttons(edit=False, view=False, record=None):
            buttons = DIV(gridbutton('buttonback', 'Back', referrer),
                          _class='form_header row_buttons %(header)s %(cornertop)s' % ui)
            if edit and (not callable(edit) or edit(record)):
                args = ['edit', table._tablename, request.args[-1]]
                buttons.append(gridbutton('buttonedit', 'Edit',
                                          url(args=args)))
            if view:
                args = ['view', table._tablename, request.args[-1]]
                buttons.append(gridbutton('buttonview', 'View',
                                          url(args=args)))
            if record and links:
                for link in links:
                    if isinstance(link, dict):
                        buttons.append(link['body'](record))
                    elif link(record):
                        buttons.append(link(record))
            return buttons

        def linsert(lst, i, x):
            """Internal use only: inserts x list into lst at i pos::

                a = [1, 2]
                linsert(a, 1, [0, 3])
                a = [1, 0, 3, 2]
            """
            lst[i:i] = x

        formfooter = DIV(
            _class='form_footer row_buttons %(header)s %(cornerbottom)s' % ui)

        create_form = update_form = view_form = search_form = None

        if create and request.args(-2) == 'new':
            table = db[request.args[-1]]
            sqlformargs = dict(ignore_rw=ignore_rw, formstyle=formstyle,
                               _class='web2py_form')
            sqlformargs.update(formargs)
            sqlformargs.update(createargs)
            create_form = SQLFORM(table, **sqlformargs)
            create_form.process(formname=formname,
                                next=referrer,
                                onvalidation=onvalidation,
                                onfailure=onfailure,
                                onsuccess=oncreate)
            res = DIV(buttons(), create_form, formfooter, _class=_class)
            res.create_form = create_form
            res.update_form = update_form
            res.view_form = view_form
            res.search_form = search_form
            res.rows = None
            return res

        elif details and request.args(-3) == 'view':
            table = db[request.args[-2]]
            record = table(request.args[-1]) or redirect(referrer)
            sqlformargs = dict(upload=upload, ignore_rw=ignore_rw,
                               formstyle=formstyle, readonly=True,
                               _class='web2py_form')
            sqlformargs.update(formargs)
            sqlformargs.update(viewargs)
            view_form = SQLFORM(table, record, **sqlformargs)
            res = DIV(buttons(edit=editable, record=record), view_form,
                      formfooter, _class=_class)
            res.create_form = create_form
            res.update_form = update_form
            res.view_form = view_form
            res.search_form = search_form
            res.rows = None
            return res
        elif editable and request.args(-3) == 'edit':
            table = db[request.args[-2]]
            record = table(request.args[-1]) or redirect(URL('error'))
            deletable_ = deletable(record) \
                if callable(deletable) else deletable
            sqlformargs = dict(upload=upload, ignore_rw=ignore_rw,
                               formstyle=formstyle, deletable=deletable_,
                               _class='web2py_form',
                               submit_button=T('Submit'),
                               delete_label=T('Check to delete'))
            sqlformargs.update(formargs)
            sqlformargs.update(editargs)
            update_form = SQLFORM(table, record, **sqlformargs)
            update_form.process(
                formname=formname,
                onvalidation=onvalidation,
                onfailure=onfailure,
                onsuccess=onupdate,
                next=referrer)
            res = DIV(buttons(view=details, record=record),
                      update_form, formfooter, _class=_class)
            res.create_form = create_form
            res.update_form = update_form
            res.view_form = view_form
            res.search_form = search_form
            res.rows = None
            return res
        elif deletable and request.args(-3) == 'delete':
            table = db[request.args[-2]]
            if not callable(deletable):
                if ondelete:
                    ondelete(table, request.args[-1])
                db(table[table._id.name] == request.args[-1]).delete()
            else:
                record = table(request.args[-1]) or redirect(URL('error'))
                if deletable(record):
                    if ondelete:
                        ondelete(table, request.args[-1])
                    record.delete_record()
            if request.ajax:
                #this means javascript is enabled, so we don't need to do
                #a redirect
                if not client_side_delete:
                    #if it's an ajax request and we don't need to reload the
                    #entire page, let's just inform that there have been no
                    #exceptions and don't regenerate the grid
                    raise HTTP(200)
                else:
                    #if it's requested that the grid gets reloaded on delete
                    #on ajax, the redirect should be on the original location
                    newloc = request.env.http_web2py_component_location
                    redirect(newloc, client_side=client_side_delete)
            else:
                #we need to do a redirect because javascript is not enabled
                redirect(referrer, client_side=client_side_delete)

        exportManager = dict(
            csv_with_hidden_cols=(ExporterCSV_hidden, 'CSV (hidden cols)', T('Comma-separated export including columns not shown; fields from other tables are exported as raw values for faster export')),
            csv=(ExporterCSV, 'CSV', T('Comma-separated export of visible columns. Fields from other tables are exported as they appear on-screen but this may be slow for many rows')),
            xml=(ExporterXML, 'XML', T('XML export of columns shown')),
            html=(ExporterHTML, 'HTML', T('HTML export of visible columns')),
            json=(ExporterJSON, 'JSON', T('JSON export of visible columns')),
            tsv_with_hidden_cols=
                (ExporterTSV, 'TSV (Spreadsheets, hidden cols)', T('Spreadsheet-optimised export of tab-separated content including hidden columns. May be slow')),
            tsv=(ExporterTSV, 'TSV (Spreadsheets)', T('Spreadsheet-optimised export of tab-separated content, visible columns only. May be slow.')))
        if not exportclasses is None:
            """
            remember: allow to set exportclasses=dict(csv=False, csv_with_hidden_cols=False) to disable the csv format
            """
            exportManager.update(exportclasses)

        export_type = request.vars._export_type
        if export_type:
            order = request.vars.order or ''
            if sortable:
                if order and not order == 'None':
                    otablename, ofieldname = order.split('~')[-1].split('.', 1)
                    sort_field = db[otablename][ofieldname]
                    exception = sort_field.type in ('date', 'datetime', 'time')
                    if exception:
                        orderby = (order[:1] == '~' and sort_field) or ~sort_field
                    else:
                        orderby = (order[:1] == '~' and ~sort_field) or sort_field

            expcolumns = [str(f) for f in columns]
            selectable_columns = [str(f) for f in columns if not isinstance(f, Field.Virtual)]
            if export_type.endswith('with_hidden_cols'):
                #expcolumns = [] start with the visible columns, which includes visible virtual fields
                selectable_columns = []  #like expcolumns but excluding virtual
                for table in tables:
                    for field in table:
                        if field.readable and field.tablename in tablenames:
                            if not str(field) in expcolumns:
                                expcolumns.append(str(field))
                            if not(isinstance(field, Field.Virtual)):
                                selectable_columns.append(str(field))
                    #look for virtual fields not displayed (and virtual method fields to be added here?)
                    for (field_name, field) in table.iteritems():
                        if isinstance(field, Field.Virtual) and not str(field) in expcolumns:
                             expcolumns.append(str(field))

            if export_type in exportManager and exportManager[export_type]:
                if request.vars.keywords:
                    try:
                        #the query should be constructed using searchable fields but not virtual fields
                        sfields = reduce(lambda a, b: a + b,
                            [[f for f in t if f.readable and not isinstance(f, Field.Virtual)] for t in tables])
                        dbset = dbset(SQLFORM.build_query(
                            sfields, request.vars.get('keywords', '')))
                        rows = dbset.select(left=left, orderby=orderby,
                                            cacheable=True, *selectable_columns)
                    except Exception, e:
                        response.flash = T('Internal Error')
                        rows = []
                else:
                    rows = dbset.select(left=left, orderby=orderby,
                                        cacheable=True, *selectable_columns)

                value = exportManager[export_type]
                clazz = value[0] if hasattr(value, '__getitem__') else value
                rows.colnames = expcolumns  # expcolumns is all cols to be exported including virtual fields
                oExp = clazz(rows)
                filename = '.'.join(('rows', oExp.file_ext))
                response.headers['Content-Type'] = oExp.content_type
                response.headers['Content-Disposition'] = \
                    'attachment;filename=' + filename + ';'
                raise HTTP(200, oExp.export(), **response.headers)

        elif request.vars.records and not isinstance(
                request.vars.records, list):
            request.vars.records = [request.vars.records]
        elif not request.vars.records:
            request.vars.records = []

        session['_web2py_grid_referrer_' + formname] = \
            url2(vars=request.get_vars)
        console = DIV(_class='web2py_console %(header)s %(cornertop)s' % ui)
        error = None
        if create:
            add = gridbutton(
                buttonclass='buttonadd',
                buttontext=T('Add Record'),
                title=T("Add record to database"),
                buttonurl=url(args=['new', tablename]))
            if not searchable:
                console.append(add)
        else:
            add = ''

        if searchable:
            sfields = reduce(lambda a, b: a + b,
                             [[f for f in t if f.readable] for t in tables])
            if isinstance(search_widget, dict):
                search_widget = search_widget[tablename]
            if search_widget == 'default':
                prefix = formname == 'web2py_grid' and 'w2p' or 'w2p_%s' % formname
                search_menu = SQLFORM.search_menu(sfields, prefix=prefix)
                spanel_id = '%s_query_fields' % prefix
                sfields_id = '%s_query_panel' % prefix
                skeywords_id = '%s_keywords' % prefix
                search_widget = lambda sfield, url: CAT(FORM(
                    INPUT(_name='keywords', _value=request.vars.keywords,
                          _id=skeywords_id,_class='form-control',
                          _onfocus="jQuery('#%s').change();jQuery('#%s').slideDown();" % (spanel_id, sfields_id) if advanced_search else ''
                          ),
                    INPUT(_type='submit', _value=T('Search'), _class="btn btn-default"),
                    INPUT(_type='submit', _value=T('Clear'), _class="btn btn-default",
                          _onclick="jQuery('#%s').val('');" % skeywords_id),
                    _method="GET", _action=url), search_menu)
            form = search_widget and search_widget(sfields, url()) or ''
            console.append(add)
            console.append(form)
            keywords = request.vars.get('keywords', '')
            try:
                if callable(searchable):
                    subquery = searchable(sfields, keywords)
                else:
                    subquery = SQLFORM.build_query(sfields, keywords)
            except RuntimeError:
                subquery = None
                error = T('Invalid query')
        else:
            subquery = None

        if subquery:
            dbset = dbset(subquery)
        try:
            nrows = fetch_count(dbset)
        except:
            nrows = 0
            error = T('Unsupported query')

        order = request.vars.order or ''
        if sortable:
            if order and not order == 'None':
                otablename, ofieldname = order.split('~')[-1].split('.', 1)
                sort_field = db[otablename][ofieldname]
                exception = sort_field.type in ('date', 'datetime', 'time')
                if exception:
                    orderby = (order[:1] == '~' and sort_field) or ~sort_field
                else:
                    orderby = (order[:1] == '~' and ~sort_field) or sort_field

        headcols = []
        if selectable:
            headcols.append(TH(_class=ui.get('default')))

        ordermatch, marker = orderby, ''
        if orderby:
            #if orderby is a single column, remember to put the marker
            if isinstance(orderby, Expression):
                if orderby.first and not orderby.second:
                    ordermatch, marker = orderby.first, '~'
        ordermatch = marker + str(ordermatch)
        for field in columns:
            if not field.readable:
                continue
            key = str(field)
            header = headers.get(str(field), field.label or key)
            if sortable and not isinstance(field, Field.Virtual):
                marker = ''
                if order:
                    if key == order:
                        key, marker = '~' + order, sorter_icons[0]
                    elif key == order[1:]:
                        marker = sorter_icons[1]
                else:
                    if key == ordermatch:
                        key, marker = '~' + ordermatch, sorter_icons[0]
                    elif key == ordermatch[1:]:
                        marker = sorter_icons[1]
                header = A(header, marker, _href=url(vars=dict(
                    keywords=request.vars.keywords or '',
                    order=key)), cid=request.cid)
            headcols.append(TH(header, _class=ui.get('default')))

        toadd = []
        left_cols = 0
        right_cols = 0
        if links and links_in_grid:
            for link in links:
                if isinstance(link, dict):
                    toadd.append(TH(link['header'], _class=ui.get('default')))
            if links_placement in ['right', 'both']:
                headcols.extend(toadd)
                right_cols += len(toadd)
            if links_placement in ['left', 'both']:
                linsert(headcols, 0, toadd)
                left_cols += len(toadd)

        # Include extra column for buttons if needed.
        include_buttons_column = (
            details or editable or deletable or
            (links and links_in_grid and
             not all([isinstance(link, dict) for link in links])))
        if include_buttons_column:
            if buttons_placement in ['right', 'both']:
                headcols.append(TH(_class=ui.get('default', '')))
                right_cols += 1
            if buttons_placement in ['left', 'both']:
                headcols.insert(0, TH(_class=ui.get('default', '')))
                left_cols += 1

        head = TR(*headcols, **dict(_class=ui.get('header')))

        cursor = True
        #figure out what page we are one to setup the limitby
        if paginate and dbset._db._adapter.dbengine == 'google:datastore':
            cursor = request.vars.cursor or True
            limitby = (0, paginate)
            try: page = int(request.vars.page or 1)-1
            except ValueError: page = 0
        elif paginate and paginate<nrows:
            try: page = int(request.vars.page or 1)-1
            except ValueError: page = 0
            limitby = (paginate*page, paginate*(page+1))
        else:
            limitby = None
        try:
            table_fields = [field for field in fields
                            if (field.tablename in tablenames and not(isinstance(field, Field.Virtual)))]
            if dbset._db._adapter.dbengine == 'google:datastore':
                rows = dbset.select(left=left, orderby=orderby,
                                    groupby=groupby, limitby=limitby,
                                    reusecursor=cursor,
                                    cacheable=True, *table_fields)
                next_cursor = dbset._db.get('_lastcursor', None)
            else:
                rows = dbset.select(left=left, orderby=orderby,
                                    groupby=groupby, limitby=limitby,
                                    cacheable=True, *table_fields)
        except SyntaxError:
            rows = None
            next_cursor = None
            error = T("Query Not Supported")
        except Exception, e:
            rows = None
            next_cursor = None
            error = T("Query Not Supported: %s") % e

        message = error
        if not message and nrows:
            if dbset._db._adapter.dbengine == 'google:datastore' and nrows >= 1000:
                message = T('at least %(nrows)s records found') % dict(nrows=nrows)
            else:
                message = T('%(nrows)s records found') % dict(nrows=nrows)
        console.append(DIV(message or '', _class='web2py_counter'))

        paginator = UL()
        if paginate and dbset._db._adapter.dbengine == 'google:datastore':
            #this means we may have a large table with an unknown number of rows.
            try:
                page = int(request.vars.page or 1)-1
            except ValueError:
                page = 0
            paginator.append(LI('page %s' % (page+1)))
            if next_cursor:
                d = dict(page=page+2, cursor=next_cursor)
                if order: d['order'] = order
                if request.vars.keywords: d['keywords'] = request.vars.keywords
                paginator.append(LI(
                    A('next', _href=url(vars=d), cid=request.cid)))
        elif paginate and paginate < nrows:
            npages, reminder = divmod(nrows, paginate)
            if reminder:
                npages += 1
            try:
                page = int(request.vars.page or 1) - 1
            except ValueError:
                page = 0

            def self_link(name, p):
                d = dict(page=p + 1)
                if order:
                    d['order'] = order
                if request.vars.keywords:
                    d['keywords'] = request.vars.keywords
                return A(name, _href=url(vars=d), cid=request.cid)
            NPAGES = 5  # window is 2*NPAGES
            if page > NPAGES + 1:
                paginator.append(LI(self_link('<<', 0)))
            if page > NPAGES:
                paginator.append(LI(self_link('<', page - 1)))
            pages = range(max(0, page - NPAGES), min(page + NPAGES, npages))
            for p in pages:
                if p == page:
                    paginator.append(LI(A(p + 1, _onclick='return false'),
                                        _class='current'))
                else:
                    paginator.append(LI(self_link(p + 1, p)))
            if page < npages - NPAGES:
                paginator.append(LI(self_link('>', page + 1)))
            if page < npages - NPAGES - 1:
                paginator.append(LI(self_link('>>', npages - 1)))
        else:
            limitby = None

        if rows:
            cols = [COL(_id=str(c).replace('.', '-'),
                        data={'column': left_cols + i + 1})
                    for i, c in enumerate(columns)]
            cols = [COL(data={'column': i + 1}) for i in range(left_cols)] + \
                   cols + \
                   [COL(data={'column': left_cols + len(cols) + i + 1})
                    for i in range(right_cols)]
            htmltable = TABLE(COLGROUP(*cols), THEAD(head))
            tbody = TBODY()
            numrec = 0
            for row in rows:
                trcols = []
                id = row[field_id]
                if selectable:
                    trcols.append(
                        INPUT(_type="checkbox", _name="records", _value=id,
                              value=request.vars.records))
                for field in columns:
                    if not field.readable:
                        continue
                    if field.type == 'blob':
                        continue
                    value = row[str(field)]
                    maxlength = maxtextlengths.get(str(field), maxtextlength)
                    if field.represent:
                        try:
                            value = field.represent(value, row)
                        except KeyError:
                            try:
                                value = field.represent(
                                    value, row[field.tablename])
                            except KeyError:
                                pass
                    elif field.type == 'boolean':
                        value = INPUT(_type="checkbox", _checked=value,
                                      _disabled=True)
                    elif field.type == 'upload':
                        if value:
                            if callable(upload):
                                value = A(
                                    T('file'), _href=upload(value))
                            elif upload:
                                value = A(T('file'),
                                          _href='%s/%s' % (upload, value))
                        else:
                            value = ''
                    if isinstance(value, str):
                        value = truncate_string(value, maxlength)
                    elif not isinstance(value, DIV):
                        value = field.formatter(value)
                    trcols.append(TD(value))
                row_buttons = TD(_class='row_buttons', _nowrap=True)
                if links and links_in_grid:
                    toadd = []
                    for link in links:
                        if isinstance(link, dict):
                            toadd.append(TD(link['body'](row)))
                        else:
                            if link(row):
                                row_buttons.append(link(row))
                    if links_placement in ['right', 'both']:
                        trcols.extend(toadd)
                    if links_placement in ['left', 'both']:
                        linsert(trcols, 0, toadd)

                if include_buttons_column:
                    if details and (not callable(details) or details(row)):
                        row_buttons.append(gridbutton(
                            'buttonview', 'View',
                            url(args=['view', tablename, id])))
                    if editable and (not callable(editable) or editable(row)):
                        row_buttons.append(gridbutton(
                            'buttonedit', 'Edit',
                            url(args=['edit', tablename, id])))
                    if deletable and (not callable(deletable) or deletable(row)):
                        row_buttons.append(gridbutton(
                            'buttondelete', 'Delete',
                            url(args=['delete', tablename, id]),
                            callback=url(args=['delete', tablename, id]),
                            noconfirm=noconfirm,
                            delete='tr'))
                    if buttons_placement in ['right', 'both']:
                        trcols.append(row_buttons)
                    if buttons_placement in ['left', 'both']:
                        trcols.insert(0, row_buttons)
                if numrec % 2 == 1:
                    classtr = 'w2p_even even'
                else:
                    classtr = 'w2p_odd odd'
                numrec += 1
                if id:
                    rid = id
                    if callable(rid):  # can this ever be callable?
                        rid = rid(row)
                    tr = TR(*trcols, **dict(
                            _id=rid,
                            _class='%s %s' % (classtr, 'with_id')))
                else:
                    tr = TR(*trcols, **dict(_class=classtr))
                tbody.append(tr)
            htmltable.append(tbody)
            htmltable = DIV(
                htmltable, _class='web2py_htmltable',
                _style='width:100%;overflow-x:auto;-ms-overflow-x:scroll')
            if selectable:
                if not callable(selectable):
                    #now expect that selectable and related parameters are iterator (list, tuple, etc)
                    inputs = []
                    for i, submit_info in enumerate(selectable):
                        submit_text = submit_info[0]
                        submit_class = submit_info[2] if len(submit_info) > 2 else ''

                        input_ctrl = INPUT(_type="submit", _name='submit_%d' % i, _value=T(submit_text))
                        input_ctrl.add_class(submit_class)
                        inputs.append(input_ctrl)
                else:
                    inputs = [INPUT(_type="submit", _value=T(selectable_submit_button))]

                if formstyle == 'bootstrap':
                    # add space between buttons
                    #inputs = sum([[inp, ' '] for inp in inputs], [])[:-1]
                    htmltable = FORM(htmltable, DIV(_class='form-actions', *inputs))
                else:
                    htmltable = FORM(htmltable, *inputs)

                if htmltable.process(formname=formname).accepted:
                    htmltable.vars.records = htmltable.vars.records or []
                    htmltable.vars.records = htmltable.vars.records if type(htmltable.vars.records) == list else [htmltable.vars.records]
                    records = [int(r) for r in htmltable.vars.records]
                    if not callable(selectable):
                        for i, submit_info in enumerate(selectable):
                            submit_callback = submit_info[1]
                            if htmltable.vars.get('submit_%d' % i, False):
                                submit_callback(records)
                                break
                    else:
                        selectable(records)
                    redirect(referrer)
        else:
            htmltable = DIV(T('No records found'))

        if csv and nrows:
            export_links = []
            for k, v in sorted(exportManager.items()):
                if not v:
                    continue
                if hasattr(v, "__getitem__"):
                    label = v[1]
                    title = v[2] if len(v)>2 else label
                else:
                    label = title = k
                link = url2(vars=dict(
                    order=request.vars.order or '',
                    _export_type=k,
                    keywords=request.vars.keywords or ''))
                export_links.append(A(T(label), _href=link, _title=title, _class='btn btn-default'))
            export_menu = \
                DIV(T('Export:'), _class="w2p_export_menu", *export_links)
        else:
            export_menu = None

        res = DIV(console, DIV(htmltable, _class="web2py_table"),
                  _class='%s %s' % (_class, ui.get('widget')))
        if paginator.components:
            res.append(
                DIV(paginator,
                    _class="web2py_paginator %(header)s %(cornerbottom)s" % ui))
        if export_menu:
            res.append(export_menu)
        res.create_form = create_form
        res.update_form = update_form
        res.view_form = view_form
        res.search_form = search_form
        res.rows = rows
        return res

    @staticmethod
    def smartgrid(table, constraints=None, linked_tables=None,
                  links=None, links_in_grid=True,
                  args=None, user_signature=True,
                  divider='>', breadcrumbs_class='',
                  **kwargs):
        """
        Builds a system of SQLFORM.grid(s) between any referenced tables

        Args:
            table: main table
            constraints(dict): `{'table':query}` that limits which records can
                be accessible
            links(dict): like `{'tablename':[lambda row: A(....), ...]}` that
                will add buttons when table tablename is displayed
            linked_tables(list): list of tables to be linked

        Example:
            given you defined a model as::

                db.define_table('person', Field('name'), format='%(name)s')
                db.define_table('dog',
                    Field('name'), Field('owner', db.person), format='%(name)s')
                db.define_table('comment', Field('body'), Field('dog', db.dog))
                if db(db.person).isempty():
                    from gluon.contrib.populate import populate
                    populate(db.person, 300)
                    populate(db.dog, 300)
                    populate(db.comment, 1000)

            in a controller, you can do::

                @auth.requires_login()
                def index():
                    form=SQLFORM.smartgrid(db[request.args(0) or 'person'])
                    return dict(form=form)

        """
        request, T = current.request, current.T
        if args is None:
            args = []

        def url(**b):
            b['args'] = request.args[:nargs] + b.get('args', [])
            b['hash_vars'] = False
            b['user_signature'] = user_signature
            return URL(**b)

        db = table._db
        breadcrumbs = []
        if request.args(len(args)) != table._tablename:
            request.args[:] = args + [table._tablename]
        if links is None:
            links = {}
        if constraints is None:
            constraints = {}
        field = None
        name = None

        def format(table, row):
            if not row:
                return T('Unknown')
            elif isinstance(table._format, str):
                return table._format % row
            elif callable(table._format):
                return table._format(row)
            else:
                return '#'+str(row.id)
        try:
            nargs = len(args) + 1
            previous_tablename, previous_fieldname, previous_id = \
                table._tablename, None, None
            while len(request.args) > nargs:
                key = request.args(nargs)
                if '.' in key:
                    id = request.args(nargs + 1)
                    tablename, fieldname = key.split('.', 1)
                    table = db[tablename]
                    field = table[fieldname]
                    field.default = id
                    referee = field.type[10:]
                    if referee != previous_tablename:
                        raise HTTP(400)
                    cond = constraints.get(referee, None)
                    if cond:
                        record = db(
                            db[referee]._id == id)(cond).select().first()
                    else:
                        record = db[referee](id)
                    if previous_id:
                        if record[previous_fieldname] != int(previous_id):
                            raise HTTP(400)
                    previous_tablename, previous_fieldname, previous_id = \
                        tablename, fieldname, id
                    name = format(db[referee], record)
                    breadcrumbs.append(
                        LI(A(T(db[referee]._plural),
                             cid=request.cid,
                             _href=url()),
                           SPAN(divider, _class='divider'),
                           _class='w2p_grid_breadcrumb_elem'))
                    if kwargs.get('details', True):
                        breadcrumbs.append(
                            LI(A(name, cid=request.cid,
                                 _href=url(args=['view', referee, id])),
                               SPAN(divider, _class='divider'),
                               _class='w2p_grid_breadcrumb_elem'))
                    nargs += 2
                else:
                    break
            if nargs > len(args) + 1:
                query = (field == id)
                # cjk
                # if isinstance(linked_tables, dict):
                #     linked_tables = linked_tables.get(table._tablename, [])
                if linked_tables is None or referee in linked_tables:
                    field.represent = lambda id, r=None, referee=referee, rep=field.represent: A(callable(rep) and rep(id) or id, cid=request.cid, _href=url(args=['view', referee, id]))
        except (KeyError, ValueError, TypeError):
            redirect(URL(args=table._tablename))
        if nargs == len(args) + 1:
            query = table._db._adapter.id_query(table)

        # filter out data info for displayed table
        if table._tablename in constraints:
            query = query & constraints[table._tablename]
        if isinstance(links, dict):
            links = links.get(table._tablename, [])
        for key in 'columns,orderby,searchable,sortable,paginate,deletable,editable,details,selectable,create,fields'.split(','):
            if isinstance(kwargs.get(key, None), dict):
                if table._tablename in kwargs[key]:
                    kwargs[key] = kwargs[key][table._tablename]
                else:
                    del kwargs[key]
        check = {}
        id_field_name = table._id.name
        for rfield in table._referenced_by:
            check[rfield.tablename] = \
                check.get(rfield.tablename, []) + [rfield.name]
        if linked_tables is None:
            linked_tables = db.tables()
        if isinstance(linked_tables, dict):
            linked_tables = linked_tables.get(table._tablename, [])

        opts = [OPTION(T('References')+':', _value='')]
        linked = []
        if linked_tables:
            for item in linked_tables:                
                tb = None
                if isinstance(item, Table) and item._tablename in check:
                    tablename = item._tablename
                    linked_fieldnames = check[tablename]
                    tb = item
                elif isinstance(item, str) and item in check:
                    tablename = item
                    linked_fieldnames = check[item]
                    tb = db[item]
                elif isinstance(item, Field) and item.name in check.get(item._tablename, []):
                    tablename = item._tablename
                    linked_fieldnames = [item.name]
                    tb = item.table
                else:
                    linked_fieldnames = []
                if tb:
                    multiple_links = len(linked_fieldnames) > 1
                    for fieldname in linked_fieldnames:
                        t = T(tb._plural) if not multiple_links else \
                            T(tb._plural + '(' + fieldname + ')')
                        args0 = tablename + '.' + fieldname
                        linked.append(
                            lambda row, t=t, nargs=nargs, args0=args0:
                                A(SPAN(t), cid=request.cid, _href=url(
                                    args=[args0, row[id_field_name]])))
        links += linked
        grid = SQLFORM.grid(query, args=request.args[:nargs], links=links,
                            links_in_grid=links_in_grid,
                            user_signature=user_signature, **kwargs)

        if isinstance(grid, DIV):
            header = table._plural
            next = grid.create_form or grid.update_form or grid.view_form
            breadcrumbs.append(LI(
                    A(T(header), cid=request.cid, _href=url()),
                    SPAN(divider, _class='divider') if next else '',
                    _class='active w2p_grid_breadcrumb_elem'))
            if grid.create_form:
                header = T('New %(entity)s') % dict(entity=table._singular)
            elif grid.update_form:
                header = T('Edit %(entity)s') % dict(
                    entity=format(grid.update_form.table,
                                  grid.update_form.record))
            elif grid.view_form:
                header = T('View %(entity)s') % dict(
                    entity=format(grid.view_form.table,
                                  grid.view_form.record))
            if next:
                breadcrumbs.append(LI(
                            A(T(header), cid=request.cid, _href=url()),
                            _class='active w2p_grid_breadcrumb_elem'))
            grid.insert(
                0, DIV(UL(*breadcrumbs, **{'_class': breadcrumbs_class}),
                       _class='web2py_breadcrumbs'))
        return grid