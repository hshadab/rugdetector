#!/usr/bin/env python3
"""
Strip ZipMap from an ONNX model exported by skl2onnx, replacing it with a tensor output.

This makes the model compatible with onnxruntime-node which doesn't support non-tensor outputs.

Strategy:
 - Find ZipMap node. Its input is a tensor of class probabilities (e.g., 'probabilities').
 - Remove ZipMap node and insert an Identity node mapping that tensor to 'output_probability'.
 - Update graph output 'output_probability' to tensor(float) shape [None, C]. If class count is known,
   we set C; otherwise, leave dims symbolic.
"""

import onnx
from onnx import helper, TensorProto
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'rugdetector_v1.onnx')

def main():
    m = onnx.load(MODEL_PATH)

    # Find ZipMap node
    zipmap_idx = None
    zipmap_node = None
    for i, n in enumerate(m.graph.node):
        if n.op_type == 'ZipMap':
            zipmap_idx = i
            zipmap_node = n
            break

    if zipmap_node is None:
        # Nothing to do
        print('No ZipMap node found; leaving model unchanged')
        return

    prob_input = zipmap_node.input[0]
    prob_output_name = zipmap_node.output[0]  # typically 'output_probability'

    # Remove ZipMap node
    nodes = list(m.graph.node)
    del nodes[ipmap := zipmap_idx]

    # Insert Identity node to preserve original output name as a tensor
    identity_node = helper.make_node(
        'Identity',
        inputs=[prob_input],
        outputs=[prob_output_name],
        name='ZipMap_To_Tensor'
    )
    nodes.insert(ipmap, identity_node)
    del m.graph.node[:]  # clear and reassign
    m.graph.node.extend(nodes)

    # Update graph output type for 'output_probability'
    # Replace the existing ValueInfo (sequence<map>) with tensor(float)
    new_outputs = []
    for ovi in m.graph.output:
        if ovi.name == prob_output_name:
            # Keep shape [None, ?]. We try to infer class count from ZipMap attributes if available.
            # Some models include attribute 'classlabels_int64s'.
            class_count = None
            for attr in zipmap_node.attribute:
                if attr.name in ('classlabels_int64s', 'classlabels_strings'):
                    class_count = len(attr.ints) if attr.ints else len(attr.strings)
                    break
            shape = [None, class_count if class_count else None]
            new_outputs.append(helper.make_tensor_value_info(prob_output_name, TensorProto.FLOAT, shape))
        else:
            new_outputs.append(ovi)

    del m.graph.output[:]
    m.graph.output.extend(new_outputs)

    # Save and verify
    onnx.checker.check_model(m)
    onnx.save(m, MODEL_PATH)
    print('Stripped ZipMap and updated output to tensor:', prob_output_name)

if __name__ == '__main__':
    main()

