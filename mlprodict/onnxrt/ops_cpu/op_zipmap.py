# -*- encoding: utf-8 -*-
"""
@file
@brief Shortcut to *ops_cpu*.
"""
from ._op import OpRun


class ZipMap(OpRun):
    """
    Implements a zip map.
    """
    atts = {'classlabels_int64s': [], 'classlabels_strings': []}

    def __init__(self, onnx_node, desc=None, **options):
        if desc is None:
            raise ValueError("desc should not be None.")
        OpRun.__init__(self, onnx_node, desc=desc,
                       expected_attributes=ZipMap.atts,
                       **options)
        if hasattr(self, 'classlabels_int64s'):
            self._zipmap = lambda x: {k: v for k,
                                      v in zip(self.classlabels_int64s, x)}  # pylint: disable=E1101
        elif hasattr(self, 'classlabels_strings'):
            self._zipmap = lambda x: {k: v for k,
                                      v in zip(self.classlabels_strings, x)}  # pylint: disable=E1101
        else:
            raise RuntimeError(
                "classlabels_int64s or classlabels_strings must be not empty.")

    def _run(self, x):  # pylint: disable=W0221
        res = [self._zipmap(_) for _ in x]
        return (res, )