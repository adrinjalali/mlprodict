"""
@file
@brief Types definition.
"""
import numpy
from .api_extension import AutoType


class MLType(AutoType):
    """
    Base class for every type.
    """

    def validate(self, value):
        """
        Checks that the value is of this type.
        """
        # It must be overwritten.
        self._cache = value

    def cast(self, value):
        """
        Converts *value* into this type.
        """
        raise NotImplementedError()


class MLNumType(MLType):
    """
    Base class for numerical types.
    """

    def _format_value_json(self, value, hook=None):
        return str(value)

    def _format_value_c(self, value, hook=None):
        return str(value)

    def _copy_c(self, src, dst, hook=None):
        if hook == "typeref":
            return "*{0} = {1};".format(dst, src)
        else:
            return "{0} = {1};".format(dst, src)


class MLNumTypeSingle(MLNumType):
    """
    int32 or float32
    """

    def __init__(self, numpy_type, name, ctype, key):
        self.numpy_type = numpy_type
        self.name = name
        self.ctype = ctype
        self.key = key

    @property
    def CTypeSingle(self):
        """
        Returns *ctype*.
        """
        return self.ctype

    def validate(self, value):
        """
        Checks that the value is of this type.
        """
        MLNumType.validate(self, value)
        if not isinstance(value, self.numpy_type):
            raise TypeError("'{0}' is not a {1}.".format(
                type(value), self.numpy_type))
        return value

    def cast(self, value):
        """
        Exports *value* into this type.
        """
        if isinstance(value, numpy.float32):
            raise TypeError(
                "No need to cast, already a {0}".format(self.numpy_type))
        if isinstance(value, numpy.ndarray):
            if len(value) != 1:
                raise ValueError(
                    "Dimension of array must be one single {0}".format(self.numpy_type))
            return value[0]
        raise NotImplementedError(
            "Unable to cast '{0}' into a {0}".format(type(self.numpy_type)))

    def softcast(self, value):
        """
        Exports *value* into this type, does it anyway without verification.
        """
        if isinstance(value, numpy.ndarray):
            v = value.ravel()
            if len(v) != 1:
                raise ValueError("Cannot cast shape {0} into {1}".format(
                    value.shape, self.numpy_type))
            return self.numpy_type(v[0])
        else:
            return self.numpy_type(value)

    def _export_common_c(self, ctype, hook=None, result_name=None):
        if hook == 'type':
            return {'code': ctype} if result_name is None else {'code': ctype + ' ' + result_name}
        elif result_name is None:
            return {'code': ctype}
        else:
            return {'code': ctype + ' ' + result_name, 'result_name': result_name}

    def _byref_c(self):
        return "&"

    def _export_json(self, hook=None, result_name=None):
        return 'float32'

    def _export_c(self, hook=None, result_name=None):
        if hook == 'typeref':
            return {'code': self.ctype + '*'} if result_name is None else {'code': self.ctype + '* ' + result_name}
        return self._export_common_c(self.ctype, hook, result_name)

    def _format_value_json(self, value, hook=None):
        if hook is None or self.key not in hook:
            return value
        return hook[self.key](value)

    def _format_value_c(self, value, hook=None):
        if hook is None or self.key not in hook:
            return "({1}){0}".format(value, self.ctype)
        return hook[self.key](value)


class MLNumTypeFloat32(MLNumTypeSingle):
    """
    A numpy.float32.
    """

    def __init__(self):
        MLNumTypeSingle.__init__(
            self, numpy.float32, 'float32', 'float', 'float32')


class MLNumTypeInt32(MLNumTypeSingle):
    """
    A numpy.int32.
    """

    def __init__(self):
        MLNumTypeSingle.__init__(self, numpy.int32, 'int32', 'int', 'int32')


class MLNumTypeBool(MLNumTypeSingle):
    """
    A numpy.bool.
    """

    def __init__(self):
        MLNumTypeSingle.__init__(self, numpy.bool, 'BL', 'bool', 'bool')


class MLTensor(MLType):
    """
    Defines a tensor with a dimension and a single type for what it contains.
    """

    def __init__(self, element_type, dim):
        if not isinstance(element_type, MLType):
            raise TypeError(
                'element_type must be of MLType not {0}'.format(type(element_type)))
        if not isinstance(dim, tuple):
            raise TypeError('dim must be a tuple.')
        if len(dim) == 0:
            raise ValueError("dimension must not be null.")
        for d in dim:
            if d == 0:
                raise ValueError("No dimension can be null.")
        self.dim = dim
        self.element_type = element_type

    @property
    def CTypeSingle(self):
        """
        Returns *ctype*.
        """
        return self.element_type.ctype

    def validate(self, value):
        """
        Checks that the value is of this type.
        """
        MLType.validate(self, value)
        if not isinstance(value, numpy.ndarray):
            raise TypeError(
                "value is not a numpy.array but '{0}'".format(type(value)))
        if self.dim != value.shape:
            raise ValueError(
                "Dimensions do not match {0}={1}".format(self.dim, value.shape))
        rvalue = value.ravel()
        for i, num in enumerate(rvalue):
            try:
                self.element_type.validate(num)
            except TypeError as e:
                raise TypeError(
                    'Unable to convert an array due to value index {0}: {1}'.format(i, rvalue[i])) from e
        return value

    def _byref_c(self):
        return ""

    def _format_value_json(self, value, hook=None):
        if hook is None or 'array' not in hook:
            return value
        return hook['array'](value)

    def _format_value_c(self, value, hook=None):
        return "{{{0}}}".format(", ".join(self.element_type._format_value_c(x) for x in value))

    def _export_json(self, hook=None, result_name=None):
        return '{0}:{1}'.format(self.element_type._export_json(hook=hook), self.dim)

    def _export_c(self, hook=None, result_name=None):
        if len(self.dim) != 1:
            raise NotImplementedError('Only 1D vector implemented.')
        if hook is None:
            raise ValueError(
                "hook must contains either 'signature' or 'declare'.")
        if hook == 'signature':
            if result_name is None:
                raise ValueError("result_name must be specified.")
            return {'code': "{0}[{1}] {2}".format(self.element_type._export_c(hook=hook)['code'],
                                                  self.dim[0], result_name),
                    'result_name': result_name}
        elif hook == 'declare':
            if result_name is None:
                raise ValueError("result_name must be specified.")
            dc = self.element_type._export_c(
                hook=hook, result_name=result_name)
            return {'code': "{0}[{1}]".format(dc['code'], self.dim[0])}
        elif hook == 'type':
            return {'code': "{0}*".format(self.element_type._export_c(hook=hook)['code'])}
        elif hook == 'typeref':
            if result_name is None:
                return {'code': "{0}*".format(self.element_type._export_c(hook='type')['code'])}
            else:
                code = self.element_type._export_c(hook='type')['code']
                return {'code': "{0}* {1}".format(code, result_name), 'result_name': result_name}
        else:
            raise ValueError(
                "hook must contains either 'signature' or 'declare' not '{0}'.".format(hook))

    def _copy_c(self, src, dest, hook=None):
        if len(self.dim) != 1:
            raise NotImplementedError('Only 1D vector implemented.')
        code = self.element_type._export_c(hook='type')['code']
        return "memcpy({1}, {0}, {2}*sizeof({3}));".format(src, dest, self.dim[0], code)
