# -*- coding: utf-8 -*-
"""
@brief      test log(time=51s)
"""
import os
import unittest
from pyquickhelper.loghelper import fLOG
from pyquickhelper.ipythonhelper import test_notebook_execution_coverage
from pyquickhelper.pycode import (
    add_missing_development_version, ExtTestCase, unittest_require_at_least,
    skipif_circleci
)
import skl2onnx
import mlprodict


class TestFunctionTestNotebookOnnxNodeTime(ExtTestCase):

    def setUp(self):
        add_missing_development_version(["jyquickhelper"], __file__, hide=True)

    @unittest_require_at_least(skl2onnx, '1.5.9999')
    @skipif_circleci("unexected issue, no benchmark is performed even it is asked")
    def test_notebook_onnx_time(self):
        fLOG(
            __file__,
            self._testMethodName,
            OutputPrint=__name__ == "__main__")

        self.assertNotEmpty(mlprodict is not None)
        folder = os.path.join(os.path.dirname(__file__),
                              "..", "..", "_doc", "notebooks")
        test_notebook_execution_coverage(__file__, "onnx_node_time", folder,
                                         this_module_name="mlprodict", fLOG=fLOG)


if __name__ == "__main__":
    unittest.main()
