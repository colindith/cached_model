from datetime import datetime

from django.core.cache import cache


class Select:
    # TODO: select should be a TreeNode Object
    def __init__(self, *args):
        self.select_path = args     # args should be a list of strings of field names

    def get_value(self, record: dict, table):
        _record = record
        path_end = False
        for field_name in self.select_path:
            if path_end:
                raise Exception('%s is not a qualified foreignkey' % field_name)
            value = _record.get(field_name)
            field = table.get_field(field_name)
            # validate if field is foreignkey
            if hasattr(field, 'foreignkey'):
                foreignkey_table = getattr(field, 'foreignkey')
                _record = foreignkey_table.get_record(value)
            else:
                path_end = True
        return _record


class WhereOperator:
    def __call__(self, lhs, rhs, operator=None):
        if not operator:
            return self.exact(lhs, rhs)
        else:
            return getattr(self, operator)(lhs, rhs)

    def exact(self, lhs, rhs):
        return lhs == rhs

    def gt(self, lhs, rhs):
        return lhs > rhs

    def gte(self, lhs, rhs):
        return lhs >= rhs

    def lt(self, lhs, rhs):
        return lhs < rhs

    def lte(self, lhs, rhs):
        return lhs <= rhs


where_operator = WhereOperator()


class WhereClause:
    def __init__(self, select, operator, value):    # operator: a str
        self.select = select
        self.operator = operator
        self.value = value

    def include_record(self, record: dict, table):
        lhs = self.select.get_value(record, table)
        rhs = self.value
        return where_operator(lhs, rhs, operator=self.operator)



class Singleton(type):
    _instance = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instance:
            cls._instance[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instance[cls]


class TableManager(metaclass=Singleton):
    def __init__(self):
        # TODO: registry model
        self.tables = dict    # memo all the tables

    def registry(self, table):
        if not hasattr(table, 'name'):
            return
        self.tables.update({
            table.name: table
        })

    def get_table(self, table_name):
        return self.tables.get(table_name)


class Table:
    # this class associated to model
    def __init__(self, timeout=600):
        # TODO: Timeout should be got from model
        self.timeout = timeout
        # self.pk_field = None
        manager = TableManager()
        manager.registry(self)

    def contribute_to_class(self, model, name):
        self.model = model
        self.name = model.__class__.__name__
        self.fields = model._meta.fields        # This is a shallow copy
        for field in self.fields:
            if field.pk:
                self.pk_field = field
                break  # only allow one pk field

        setattr(model, name, self)    # TODO: Here should use Descriptor

    def get_field(self, field_name):
        for field in self.fields:
            if field.name == field_name:
                return field
        return None

    def get_pk_list_cache_key(self):
        return 'cached-table-%s-pk-list' % self.name
        # OrderedDict[(pk_1, expire_time_1), (pk_2, expire_time_2)...]

    def get_pk_list(self):
        pk_list = cache.get(self.get_pk_list_cache_key())
        if not pk_list:
            pk_list = []
        return pk_list

    # def update_pk_list(self):

    def refresh_expired(self):
        pk_list = self.get_pk_list()
        _timestamp = datetime.now().timestamp()
        del_key_list = []
        for key, value in pk_list.items():
            if value < _timestamp:
                del_key_list.append(key)
        for key in del_key_list:
            del pk_list[key]

    def get_meta_cache_key(self):
        return 'cached-table-%s-meta' % self.name

    def get_record_cache_key(self, pk):
        return 'cached-table-%s-%s' % (self.name, pk)

    def get_record(self, pk):
        record = cache.get(self.get_record_cache_key(pk))
        if not record:
            raise Exception
        return record
    # def save(self, data):
    #     # for update or create
    #     pk = data.get(self.pk_field.name)

    def create(self, data):
        # data should be a dictionary, key=field_name, value=data
        # need validate
        pk = data.get(self.pk_field.name)
        pk_list = self.get_pk_list()

        if pk:
            # check if pk exist

            if pk in pk_list:
                raise Exception
        else:
            if not self.pk_field.auto_incr:
                raise Exception
            meta = cache.get(self.get_meta_cache_key())
            if not meta:
                meta = {'pk_count': 0}
            pk = meta['pk_count']
            meta['pk_count'] += 1
            data[self.pk_field.name] = pk
            cache.set(self.get_meta_cache_key(), meta, timeout=self.timeout)

        ########## update pk_list ##########
        _timestamp = datetime.now().timestamp()
        pk_list.append((pk, _timestamp + self.timeout))
        cache.set(self.get_pk_list_cache_key(), pk_list, timeout=self.timeout)
        ########################################
        cache.set(self.get_record_cache_key(pk), data, timeout=self.timeout)

    def update(self, data):
        pk = data.get(self.pk_field.name)
        if not pk:
            raise Exception
        pk_list = self.get_pk_list()
        if pk not in pk_list:
            raise Exception
        _data = cache.get(self.get_record_cache_key(pk))
        for key, value in data.items():
            _data[key] = value
        cache.set(self.get_pk_list_cache_key(), pk_list, timeout=self.timeout)

        _timestamp = datetime.now().timestamp()
        pk_list[pk] = _timestamp + self.timeout
        cache.set(self.get_record_cache_key(pk), data, timeout=self.timeout)

    def get(self, pk):
        _data = cache.get(self.get_record_cache_key(pk))
        return _data

    def query(self, where=None, select=None, order_by=None, opt=None):
        # where:    [(field, expression, value), ...]   TODO: where should support foreign key
        # select:   [field, ...]        TODO: select may contain foreign key like `plan__game`. This should be handled
        # order_by: (field, reverse=False)
        # TODO: oreder_by should take in multiple values

        pk_list = self.get_pk_list()
        if opt:
            flat = opt.get('flat')
        else:
            flat = False
        if order_by:
            order_by_field = order_by[0]
            order_by_reverse = order_by[1]
            self.sort_by_field(pk_list, order_by_field, order_by_reverse)
            # Here order all record in  table

        res_list = []

        for pk in pk_list:
            record = cache.get(self.get_record_cache_key(pk[0]))
            _include = True
            for where_clause in where:
                if not where_clause.include_record(record):
                    _include = False
                    break

            if select:
                _record = {}
                for select_clause in select:
                    _record = select_clause.get_value(record, self)

                if flat:
                    _record = tuple(_record.values())
            else:
                _record = record
            res_list.append(_record)
        return res_list

    @staticmethod
    def sort_by_field(record_list, field, reverse):
        return sorted(
            record_list.items(),
            key=lambda x: x[field.name],
            reverse=reverse
        )
