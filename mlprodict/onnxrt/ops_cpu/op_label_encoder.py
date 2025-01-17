# -*- encoding: utf-8 -*-
# pylint: disable=E0203,E1101,C0111
"""
@file
@brief Runtime operator.
"""
import numpy
from ._op import OpRun


class LabelEncoder(OpRun):

    atts = {'default_float': 0., 'default_int64': -1,
            'default_string': b'',
            'keys_floats': numpy.empty(0, dtype=numpy.float32),
            'keys_int64s': numpy.empty(0, dtype=numpy.int64),
            'keys_strings': numpy.empty(0, dtype=numpy.str),
            'values_floats': numpy.empty(0, dtype=numpy.float32),
            'values_int64s': numpy.empty(0, dtype=numpy.int64),
            'values_strings': numpy.empty(0, dtype=numpy.str),
            }

    def __init__(self, onnx_node, desc=None, **options):
        OpRun.__init__(self, onnx_node, desc=desc,
                       expected_attributes=LabelEncoder.atts,
                       **options)
        if len(self.keys_floats) > 0:
            self.classes_ = {k: v for k, v in zip(
                self.keys_floats, self.values_floats)}
            self.default_ = self.default_float
            self.dtype_ = numpy.float32
        elif len(self.keys_int64s) > 0:
            self.classes_ = {k: v for k, v in zip(
                self.keys_int64s, self.values_int64s)}
            self.default_ = self.default_int64
            self.dtype_ = numpy.int64
        elif len(self.keys_strings) > 0:
            self.classes_ = {k: v for k, v in zip(
                self.keys_strings, self.values_strings)}
            self.default_ = self.default_string
            self.dtype_ = numpy.str
        elif hasattr(self, 'classes_strings'):
            raise RuntimeError("This runtime does not implement version 1 of "
                               "operator LabelEncoder.")
        else:
            raise RuntimeError("No encoding was defined.")

    def _run(self, x):  # pylint: disable=W0221
        res = numpy.empty((x.shape[0], ), dtype=self.dtype_)
        for i in range(0, res.shape[0]):
            res[i] = self.classes_.get(x[i], self.default_)
        return (res, )
