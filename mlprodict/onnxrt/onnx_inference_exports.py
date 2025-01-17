"""
@file
@brief Extensions to class @see cl OnnxInference.
"""
import json
from onnx import numpy_helper
from .onnx2py_helper import _var_as_dict, _type_to_string


class OnnxInferenceExport:
    """
    Implements methods to export a instance of
    @see cl OnnxInference into :epkg:`json` or :epkg:`dot`.
    """

    def __init__(self, oinf):
        """
        @param      oinf    @see cl OnnxInference
        """
        self.oinf = oinf

    def to_dot(self, recursive=False, prefix='', add_rt_shapes=False, **params):
        """
        Produces a :epkg:`DOT` language string for the graph.

        @param      params          additional params to draw the graph
        @param      recursive       also show subgraphs inside operator like
                                    @see cl Scan
        @param      prefix          prefix for every node name
        @param      add_rt_shapes   adds shapes infered from the python runtime
        @return                     string

        Default options for the graph are:

        ::

            options = {
                'orientation': 'portrait',
                'ranksep': '0.25',
                'nodesep': '0.05',
                'width': '0.5',
                'height': '0.1',
            }

        One example:

        .. exref::
            :title: Convert ONNX into DOT

            An example on how to convert an :epkg:`ONNX`
            graph into :epkg:`DOT`.

            .. runpython::
                :showcode:

                import numpy
                from skl2onnx.algebra.onnx_ops import OnnxLinearRegressor
                from skl2onnx.common.data_types import FloatTensorType
                from mlprodict.onnxrt import OnnxInference

                pars = dict(coefficients=numpy.array([1., 2.]),
                            intercepts=numpy.array([1.]),
                            post_transform='NONE')
                onx = OnnxLinearRegressor('X', output_names=['Y'], **pars)
                model_def = onx.to_onnx({'X': pars['coefficients'].astype(numpy.float32)},
                                        outputs=[('Y', FloatTensorType([1]))])
                oinf = OnnxInference(model_def)
                print(oinf.to_dot())

            See an example of representation in notebook
            :ref:`onnxvisualizationrst`.
        """
        options = {
            'orientation': 'portrait',
            'ranksep': '0.25',
            'nodesep': '0.05',
            'width': '0.5',
            'height': '0.1',
        }
        options.update(params)

        inter_vars = {}
        exp = ["digraph{"]
        for opt in {'orientation', 'pad', 'nodesep', 'ranksep'}:
            if opt in options:
                exp.append("  {}={};".format(opt, options[opt]))
        fontsize = 10

        shapes = {}
        if add_rt_shapes:
            if not hasattr(self.oinf, 'shapes_'):
                raise RuntimeError(
                    "No information on shapes, check the runtime '{}'.".format(self.oinf.runtime))
            for name, shape in self.oinf.shapes_.items():
                va = shape.evaluate().to_string()
                shapes[name] = va
                if name in self.oinf.inplaces_:
                    shapes[name] += "\\ninplace"

        # inputs
        exp.append("")
        for obj in self.oinf.obj.graph.input:
            dobj = _var_as_dict(obj)
            sh = shapes.get(dobj['name'], '')
            if sh:
                sh = "\\nshape={}".format(sh)
            exp.append('  {3}{0} [shape=box color=red label="{0}\\n{1}{4}" fontsize={2}];'.format(
                dobj['name'], _type_to_string(dobj['type']), fontsize, prefix, sh))
            inter_vars[obj.name] = obj

        # outputs
        exp.append("")
        for obj in self.oinf.obj.graph.output:
            dobj = _var_as_dict(obj)
            sh = shapes.get(dobj['name'], '')
            if sh:
                sh = "\\nshape={}".format(sh)
            exp.append('  {3}{0} [shape=box color=green label="{0}\\n{1}{4}" fontsize={2}];'.format(
                dobj['name'], _type_to_string(dobj['type']), fontsize, prefix, sh))
            inter_vars[obj.name] = obj

        # initializer
        exp.append("")
        for obj in self.oinf.obj.graph.initializer:
            dobj = _var_as_dict(obj)
            val = dobj['value']
            flat = val.flatten()
            if flat.shape[0] < 9:
                st = str(val)
            else:
                st = str(val)
                if len(st) > 30:
                    st = st[:30] + '...'
            st = st.replace('\n', '\\n')
            kind = ""
            exp.append('  {6}{0} [shape=box label="{0}\\n{4}{1}({2})\\n{3}" fontsize={5}];'.format(
                dobj['name'], dobj['value'].dtype,
                dobj['value'].shape, st, kind, fontsize, prefix))
            inter_vars[obj.name] = obj

        # nodes
        for node in self.oinf.obj.graph.node:
            exp.append("")
            for out in node.output:
                if out not in inter_vars:
                    inter_vars[out] = out
                    sh = shapes.get(out, '')
                    if sh:
                        sh = "\\nshape={}".format(sh)
                    exp.append(
                        '  {2}{0} [shape=box label="{0}{3}" fontsize={1}];'.format(
                            out, fontsize, prefix, sh))

            dobj = _var_as_dict(node)
            if dobj['name'].strip() == '':
                raise RuntimeError(
                    "Issue with a node\n{}\n----\n{}".format(dobj, node))

            atts = []
            if 'atts' in dobj:
                for k, v in sorted(dobj['atts'].items()):
                    val = None
                    if 'value' in v:
                        val = str(v['value']).replace(
                            "\n", "\\n").replace('"', "'")
                        sl = max(30 - len(k), 10)
                        if len(val) > sl:
                            val = val[:sl] + "..."
                    if val is not None:
                        atts.append('{}={}'.format(k, val))
            satts = "" if len(atts) == 0 else ("\\n" + "\\n".join(atts))

            if recursive and node.op_type in {'Scan'}:
                # creates the subgraph
                body = dobj['atts']['body']['value']
                oinf = self.oinf.__class__(
                    body, runtime=self.oinf.runtime, skip_run=self.oinf.skip_run)
                subprefix = prefix + "B_"
                subdot = oinf.to_dot(recursive=recursive, prefix=subprefix,
                                     add_rt_shapes=add_rt_shapes)
                lines = subdot.split("\n")
                start = 0
                for i, line in enumerate(lines):
                    if '[' in line:
                        start = i
                        break
                subgraph = "\n".join(lines[start:])

                # connecting the subgraph
                exp.append("  subgraph cluster_{}{} {{".format(
                    node.op_type, id(node)))
                exp.append('    label="{0}\\n({1}){2}";'.format(
                    dobj['op_type'], dobj['name'], satts))
                exp.append('    fontsize={0};'.format(fontsize))
                exp.append('    color=black;')
                exp.append(
                    '\n'.join(map(lambda s: '  ' + s, subgraph.split('\n'))))

                for inp1, inp2 in zip(node.input, body.input):
                    exp.append(
                        "  {0}{1} -> {2}{3};".format(prefix, inp1, subprefix, inp2.name))
                for out1, out2 in zip(body.output, node.output):
                    exp.append(
                        "  {0}{1} -> {2}{3};".format(subprefix, out1.name, prefix, out2))

            else:
                exp.append('  {4}{1} [shape=box style="filled,rounded" color=orange label="{0}\\n({1}){2}" fontsize={3}];'.format(
                    dobj['op_type'], dobj['name'], satts, fontsize, prefix))

                for inp in node.input:
                    exp.append(
                        "  {0}{1} -> {0}{2};".format(prefix, inp, node.name))
                for out in node.output:
                    exp.append(
                        "  {0}{1} -> {0}{2};".format(prefix, node.name, out))

        exp.append('}')
        return "\n".join(exp)

    def to_json(self, indent=2):
        """
        Converts an :epkg:`ONNX` model into :epkg:`JSON`.

        @param      indent      indentation
        @return                 string

        .. exref::
            :title: Convert ONNX into JSON

            An example on how to convert an :epkg:`ONNX`
            graph into :epkg:`JSON`.

            .. runpython::
                :showcode:

                import numpy
                from skl2onnx.algebra.onnx_ops import OnnxLinearRegressor
                from skl2onnx.common.data_types import FloatTensorType
                from mlprodict.onnxrt import OnnxInference

                pars = dict(coefficients=numpy.array([1., 2.]),
                            intercepts=numpy.array([1.]),
                            post_transform='NONE')
                onx = OnnxLinearRegressor('X', output_names=['Y'], **pars)
                model_def = onx.to_onnx({'X': pars['coefficients'].astype(numpy.float32)},
                                        outputs=[('Y', FloatTensorType([1]))])
                oinf = OnnxInference(model_def)
                print(oinf.to_json())
        """

        def _to_json(obj):
            s = str(obj)
            rows = ['{']
            leave = None
            for line in s.split('\n'):
                if line.endswith("{"):
                    rows.append('"%s": {' % line.strip('{ '))
                elif ':' in line:
                    spl = line.strip().split(':')
                    if len(spl) != 2:
                        raise RuntimeError(
                            "Unable to interpret line '{}'.".format(line))

                    if spl[0].strip() in ('type', ):
                        st = spl[1].strip()
                        if st in {'INT', 'INTS', 'FLOAT', 'FLOATS', 'STRING', 'STRINGS'}:
                            spl[1] = '"{}"'.format(st)

                    if spl[0] in ('floats', 'ints'):
                        if leave:
                            rows.append("{},".format(spl[1]))
                        else:
                            rows.append('"{}": [{},'.format(
                                spl[0], spl[1].strip()))
                            leave = spl[0]
                    elif leave:
                        rows[-1] = rows[-1].strip(',')
                        rows.append('],')
                        rows.append('"{}": {},'.format(
                            spl[0].strip(), spl[1].strip()))
                        leave = None
                    else:
                        rows.append('"{}": {},'.format(
                            spl[0].strip(), spl[1].strip()))
                elif line.strip() == "}":
                    rows[-1] = rows[-1].rstrip(",")
                    rows.append(line + ",")
                elif line:
                    raise RuntimeError(
                        "Unable to interpret line '{}'.".format(line))
            rows[-1] = rows[-1].rstrip(',')
            rows.append("}")
            js = "\n".join(rows)

            try:
                content = json.loads(js)
            except json.decoder.JSONDecodeError as e:
                js2 = "\n".join("%04d %s" % (i + 1, line)
                                for i, line in enumerate(js.split("\n")))
                raise RuntimeError(
                    "Unable to parse JSON\n{}".format(js2)) from e
            return content

        # meta data
        final_obj = {}
        for k in {'ir_version', 'producer_name', 'producer_version',
                  'domain', 'model_version', 'doc_string'}:
            if hasattr(self.oinf.obj, k):
                final_obj[k] = getattr(self.oinf.obj, k)

        # inputs
        inputs = []
        for obj in self.oinf.obj.graph.input:
            st = _to_json(obj)
            inputs.append(st)
        final_obj['inputs'] = inputs

        # outputs
        outputs = []
        for obj in self.oinf.obj.graph.output:
            st = _to_json(obj)
            outputs.append(st)
        final_obj['outputs'] = outputs

        # init
        inits = {}
        for obj in self.oinf.obj.graph.initializer:
            value = numpy_helper.to_array(obj).tolist()
            inits[obj.name] = value
        final_obj['initializers'] = inits

        # nodes
        nodes = []
        for obj in self.oinf.obj.graph.node:
            node = dict(name=obj.name, op_type=obj.op_type, domain=obj.domain,
                        inputs=[str(_) for _ in obj.input],
                        outputs=[str(_) for _ in obj.output],
                        attributes={})
            for att in obj.attribute:
                st = _to_json(att)
                node['attributes'][st['name']] = st
                del st['name']
            nodes.append(node)
        final_obj['nodes'] = nodes

        return json.dumps(final_obj, indent=indent)
