

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
