import inspect
from datetime import datetime

from django.core.cache import cache

from .manager import Manager


class Field:
    def __init__(self, timeout=None, name=None, auto_created=None, primary_key=None, **kwargs):
        self.timeout = timeout or 600
        self.pk = primary_key
        self.name = name
        self.attname = name
        self.auto_created = auto_created
        self.auto_incr = False

    def contribute_to_class(self, cls, name, private_only=False):
        """
        Register the field with the model class it belongs to.

        If private_only is True, create a separate instance of this field
        for every subclass of cls, even if cls is not an abstract model.
        """
        self.model = cls
        self.name = name
        self.attname = name
        cls._meta.add_field(field=self)


class AutoField(Field):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.auto_created = True
        self.pk = True
        self.auto_incr = True

    def contribute_to_class(self, cls, name, private_only=False):
        super().contribute_to_class(cls, name, private_only=False)


class Table:
    # this class associated to model
    def __init__(self, name=None, fields=None, timeout=600):
        # TODO: Timeout should be got from model
        self.timeout = timeout
        # self.pk_field = None

    def contribute_to_class(self, model, name):
        self.model = model
        self.name = model.__class__.__name__
        self.fields = model._meta.fields        # This is a shallow copy
        for field in self.fields:
            if field.pk:
                self.pk_field = field
                break  # only allow one pk field

        setattr(model, name, self)    # TODO: Here should use Descriptor

    def get_all_pk_cache_key(self):
        return 'cached-table-%s-pk-list' % self.name
        # OrderedDict[(pk_1, expire_time_1), (pk_2, expire_time_2)...]

    def get_record_list(self):
        record_list = cache.get(self.get_all_pk_cache_key())
        if not record_list:
            record_list = []
        return record_list

    # def update_record_list(self):

    def refresh_expired(self):
        record_list = self.get_record_list()
        _timestamp = datetime.now().timestamp()
        del_key_list = []
        for key, value in record_list.items():
            if value < _timestamp:
                del_key_list.append(key)
        for key in del_key_list:
            del record_list[key]

    def get_meta_cache_key(self):
        return 'cached-table-%s-meta-list' % self.name

    def get_record_cache_key(self, pk):
        return 'cached-table-%s-%s-list' % (self.name, pk)

    # def save(self, data):
    #     # for update or create
    #     pk = data.get(self.pk_field.name)

    def create(self, data):
        # data should be a dictionary, key=field_name, value=data
        # need validate
        pk = data.get(self.pk_field.name)
        record_list = self.get_record_list()

        if pk:
            # check if pk exist

            if pk in record_list:
                raise Exception
        else:
            if not self.pk_field.auto_incr:
                raise Exception
            meta = cache.get(self.get_meta_cache_key())
            if not meta:
                meta = {'pk_count': 0}
            pk = meta['pk_count'] + 1
            meta['pk_count'] = pk
            data[self.pk_field.name] = pk
            record_list.append(pk)
            cache.set(self.get_meta_cache_key(), meta, timeout=self.timeout)

        ########## update record_list ##########
        _timestamp = datetime.now().timestamp()
        record_list.append((pk, _timestamp + self.timeout))
        cache.set(self.get_record_cache_key(pk), record_list, timeout=self.timeout)
        ########################################
        cache.set(self.get_record_cache_key(pk), data, timeout=self.timeout)

    def update(self, data):
        pk = data.get(self.pk_field.name)
        if not pk:
            raise Exception
        record_list = self.get_record_list()
        if pk not in record_list:
            raise Exception
        _data = cache.get(self.get_record_cache_key(pk))
        for key, value in data.items():
            _data[key] = value
        cache.set(self.get_record_cache_key(pk), data, timeout=self.timeout)

        _timestamp = datetime.now().timestamp()
        record_list[pk] = _timestamp + self.timeout
        cache.set(self.get_record_cache_key(pk), record_list, timeout=self.timeout)

    def get(self, pk):
        _data = cache.get(self.get_record_cache_key(pk))
        return _data

    def query(self, where=None, select=None, order_by=None, opt=None):
        # where:    [(field, expression, value), ...]   TODO: where should support foreign key
        # select:   [field, ...]        TODO: select may contain foreign key like `plan__game`. This should be handled
        # order_by: (field, reverse=False)
        # TODO: oreder_by should take in multiple values

        record_list = self.get_record_list()
        print(f'record_list: {record_list}')
        if opt:
            flat = opt.get('flat')
        else:
            flat = False
        if order_by:
            order_by_field = order_by[0]
            order_by_reverse = order_by[1]
            self.sort_by_field(record_list, order_by_field, order_by_reverse)
            # Here order all record in  table

        res_list = []

        for record in record_list:
            _include = True
            for where_clause in where:
                field = where_clause[0]
                expression = where_clause[1]
                value = where_clause[2]
                if not getattr(field, expression)(record[field.name], value):
                    _include = False
                    break   # break to next record if any where clause is not met
            if select:
                _record = {}
                for select_clause in select:
                    field = select_clause
                    _record[field.name] = record[field.name]
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



class Options:
    def __init__(self):
        self.fields = []

    def add_field(self, field):
        self.fields.append(field)

class ModelBase(type):
    def __new__(cls, name, bases, attrs, **kwargs):
        super_new = super().__new__
        new_class = super_new(cls, name, bases, attrs, **kwargs)



        new_class.add_to_class('_meta', Options())
        manager = Manager()
        new_class.add_to_class('objects', manager)

        # Add all attributes to the class.
        for obj_name, obj in attrs.items():
            new_class.add_to_class(obj_name, obj)

        fields = new_class._meta.fields
        default_pk = True
        for field in fields:
            if field.pk:
                setattr(new_class, 'pk_field', field)
                default_pk = False

        if default_pk:
            default_pk_field = AutoField(name='id')
            new_class.add_to_class('id', default_pk_field)
            setattr(new_class, 'pk_field', default_pk_field)

        new_class.add_to_class('table', Table())

        return new_class

    def add_to_class(self, name, value):
        # We should call the contribute_to_class method only if it's bound
        if not inspect.isclass(value) and hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(self, name)
        else:
            setattr(self, name, value)




class Model(metaclass=ModelBase):
    def __init__(self, *args, **kwargs):
        self.name = self.__class__.__name__
        _setattr = setattr

        _setattr(self, self.pk_field.name, None)

        if not kwargs:
            # TODO: Defered field should be load later
            for val, field in zip(args, self._meta.fields):
                _setattr(self, field.attname, val)
        else:
            # Slower, kwargs-ready version.
            for val, field in zip(args, self._meta.fields):
                _setattr(self, field.attname, val)
                kwargs.pop(field.name, None)
            for field_name, val in kwargs.items():
                _setattr(self, field_name, val)


    def save(self):
        data = {
            field.attname: getattr(self, field.attname)
            for field in self._meta.fields
        }
        try:
            self.table.update(data)
        except:
            # no pk or pk not in record list
            self.table.create(data)





class Singleton(type):
    _instance = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instance:
            cls._instance[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instance[cls]


class TableManager(metaclass=Singleton):
    def __init__(self):
        # TODO: registry model
        self.tables = []    # memo all the tables

    # def _get_cache

