from .cached_table import TableManager


class Field:
    def __init__(self, timeout=None, name=None, auto_created=None, primary_key=None, default=None, auto_now_add=False, **kwargs):
        self.timeout = timeout or 600
        self.pk = primary_key
        self.name = name
        self.attname = name
        self.auto_created = auto_created
        self.auto_incr = False
        self.default = default
        self.auto_now_add = auto_now_add

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


class ForeignKey(Field):
    def __init__(self, model, **kwargs):
        super().__init__(**kwargs)
        manager = TableManager()
        # foreignkey reference the Table instance
        self.foreignkey = manager.get_table(model.__class__.__name__)
        related_name = kwargs.get('related_name')
        if not related_name:
            related_name = '%s_%s' % (self.model.name, self.foreignkey.name)
        # TODO: add a foreign key to the corresponding model with attname as $related_name

    def contribute_to_class(self, cls, name, private_only=False):
        super().contribute_to_class(cls, name, private_only=False)
