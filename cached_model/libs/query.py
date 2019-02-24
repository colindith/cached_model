
GET_ITERATOR_CHUNK_SIZE = 100

# The maximum number of items to display in a QuerySet.__repr__
REPR_OUTPUT_SIZE = 20


class BaseIterable:
    def __init__(self, queryset, chunked_fetch=False, chunk_size=GET_ITERATOR_CHUNK_SIZE):
        self.queryset = queryset
        self.chunked_fetch = chunked_fetch
        self.chunk_size = chunk_size


class ModelIterable(BaseIterable):
    """Iterable that yields a model instance for each row."""

    def __iter__(self):
        queryset = self.queryset


        results = queryset.excute_sql()










        # db = queryset.db
        # compiler = queryset.query.get_compiler(using=db)
        # # Execute the query. This will also fill compiler.select, klass_info,
        # # and annotations.
        # results = compiler.execute_sql(chunked_fetch=self.chunked_fetch, chunk_size=self.chunk_size)
        # select, klass_info, annotation_col_map = (compiler.select, compiler.klass_info,
        #                                           compiler.annotation_col_map)
        # model_cls = klass_info['model']
        # select_fields = klass_info['select_fields']
        # model_fields_start, model_fields_end = select_fields[0], select_fields[-1] + 1
        # init_list = [f[0].target.attname
        #              for f in select[model_fields_start:model_fields_end]]
        # related_populators = get_related_populators(klass_info, select, db)






        for row in results:
            obj = None
            # obj = model_cls.from_db(db, init_list, row[model_fields_start:model_fields_end])
            # for rel_populator in related_populators:
            #     rel_populator.populate(row, obj)
            # if annotation_col_map:
            #     for attr_name, col_pos in annotation_col_map.items():
            #         setattr(obj, attr_name, row[col_pos])

            # Add the known related objects to the model, if there are any
            # if queryset._known_related_objects:
            #     for field, rel_objs in queryset._known_related_objects.items():
            #         # Avoid overwriting objects loaded e.g. by select_related
            #         if field.is_cached(obj):
            #             continue
            #         pk = getattr(obj, field.get_attname())
            #         try:
            #             rel_obj = rel_objs[pk]
            #         except KeyError:
            #             pass  # may happen in qs1 | qs2 scenarios
            #         else:
            #             setattr(obj, field.name, rel_obj)

            yield row


class QuerySet:


    def __init__(self, model=None, query=None, using=None, hints=None):
        self.model = model  # this model should have been populated by manager
        self._db = using
        self._hints = hints or {}

        # self.query = query or sql.Query(self.model) TODO: This should be in a query object
        self.where = []     # [(lhs, rhs, expression, negate=True), ()...]
        self.select = []
        self.order_by = ()
        self.limit = ()

        self._result_cache = None
        self._sticky_filter = False
        self._for_write = False
        self._prefetch_related_lookups = ()
        self._prefetch_done = False
        self._known_related_objects = {}  # {rel_field: {pk: rel_obj}}
        # self._iterable_class = ModelIterable
        self._fields = None

        self._iterable_class = ModelIterable

    def __repr__(self):
        data = list(self[:REPR_OUTPUT_SIZE + 1])
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."
        return '<%s %r>' % (self.__class__.__name__, data)

    def __iter__(self):
        # return self._iterable_class(self)
        return iter(self._iterable_class(self))

    def __getitem__(self, k):
        """Retrieve an item or slice from the set of results."""
        if not isinstance(k, (int, slice)):
            raise TypeError
        # TODO: implment negative indexing
        assert ((not isinstance(k, slice) and (k >= 0)) or
                (isinstance(k, slice) and (k.start is None or k.start >= 0) and
                 (k.stop is None or k.stop >= 0))), \
            "Negative indexing is not supported."

        if self._result_cache is not None:
            return self._result_cache[k]

        if isinstance(k, slice):
            qs = self
            if k.start is not None:
                start = int(k.start)
            else:
                start = None
            if k.stop is not None:
                stop = int(k.stop)
            else:
                stop = None
            qs.set_limits(start, stop)
            return list(qs)[::k.step] if k.step else qs

        qs = self
        qs.set_limits(k, k + 1)
        qs._fetch_all()
        return qs._result_cache[0]

    def create(self, **kwargs):
        obj = self.model(**kwargs)
        obj.save()
        return obj

    def first(self):
        """Return the first object of a query or None if no match is found."""
        print(f'========== queryset first ========')
        for obj in (self if self.ordered else self.order_by('pk'))[:1]:
            return obj

    def all(self):
        """
        Return a new QuerySet that is a copy of the current one. This allows a
        QuerySet to proxy for a model manager in some cases.
        """
        print(f'========== queryset all ========')
        return self

    def filter(self, *args, **kwargs):
        """
        Return a new QuerySet instance with the args ANDed to the existing
        set.
        """
        return self._filter_or_exclude(False, *args, **kwargs)

    def exclude(self, *args, **kwargs):
        """
        Return a new QuerySet instance with NOT (args) ANDed to the existing
        set.
        """
        return self._filter_or_exclude(True, *args, **kwargs)

    def _filter_or_exclude(self, negate, *args, **kwargs):
        # if args or kwargs:
        #     assert self.query.can_filter(), \
        #         "Cannot filter a query once a slice has been taken."
        if negate:
            self.where += [(v, k, negate) for k, v in kwargs.items()]
        else:
            self.where += [(v, k, negate) for k, v in kwargs.items()]
        return self

    def _fetch_all(self):
        # populate the _result_cache. This function should be call whenever before listing or getitem
        if self._result_cache is None:
            self._result_cache = list(self._iterable_class(self))

    def excute_sql(self):
        # TODO: implement the real query here
        table = self.model.table
        result = table.query(where=self.where, select=self.select, order_by=self.order_by, opt=None)


        return result

    def set_limits(self, start, stop):
        self.limit = (start, stop)


