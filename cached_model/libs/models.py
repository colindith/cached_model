import inspect
from django.utils import timezone
from .manager import Manager
from .cached_table import Table
from .fields import Field, AutoField, ForeignKey



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
        # TODO: Why Django models won't have Field object when create???
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
        data = dict()
        for field in self._meta.fields:
            if hasattr(self, field.attname) and not isinstance(getattr(self, field.attname), Field): # TODO: remove the 2nd expression and fill-in in models creation
                data.update({
                    field.attname: getattr(self, field.attname)
                })
            elif field.default:
                data.update({field.attname: field.default})
            elif field.auto_now_add:
                data.update({field.attname: timezone.localtime()})
            else:
                data.update({field.attname: None})
        try:
            self.table.update(data)
        except:
            # no pk or pk not in record list
            self.table.create(data)
