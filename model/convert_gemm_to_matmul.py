#!/usr/bin/env python3
"""
Convert Gemm nodes to MatMul + Add for Jolt-Atlas compatibility
onnx-tracer only supports MatMul, not Gemm
"""

import onnx
from onnx import helper, numpy_helper
import sys

def convert_gemm_to_matmul(input_path, output_path):
    """
    Replace Gemm nodes with MatMul + Add nodes

    Gemm: Y = alpha * A @ B + beta * C
    When alpha=1, beta=1: Y = A @ B + C (standard linear layer)

    Converts to:
    - MatMul: temp = A @ B
    - Add: Y = temp + C
    """
    print(f"🔧 Converting Gemm to MatMul+Add: {input_path}")

    # Load model
    model = onnx.load(input_path)
    graph = model.graph

    new_nodes = []
    nodes_to_remove = []

    for node in graph.node:
        if node.op_type == 'Gemm':
            print(f"   Converting Gemm node: {node.name}")

            # Extract inputs: [A, B, C] where C is bias
            input_a = node.input[0]  # activation
            input_b = node.input[1]  # weight
            input_c = node.input[2] if len(node.input) > 2 else None  # bias
            output = node.output[0]

            # Get attributes (alpha, beta, transA, transB)
            alpha = 1.0
            beta = 1.0
            trans_a = 0
            trans_b = 0

            for attr in node.attribute:
                if attr.name == 'alpha':
                    alpha = attr.f
                elif attr.name == 'beta':
                    beta = attr.f
                elif attr.name == 'transA':
                    trans_a = attr.i
                elif attr.name == 'transB':
                    trans_b = attr.i

            # Sanity check: we only support standard Gemm (alpha=1, beta=1)
            if alpha != 1.0 or beta != 1.0:
                print(f"⚠️  Warning: Gemm has alpha={alpha}, beta={beta}, may not work correctly")

            # Gemm typically has transB=1 (weight matrix is transposed)
            # Need to add Transpose node before MatMul if transB=1
            matmul_input_b = input_b
            if trans_b == 1:
                # Add Transpose node for weight
                transpose_output = f"{input_b}_transposed"
                transpose_node = helper.make_node(
                    'Transpose',
                    inputs=[input_b],
                    outputs=[transpose_output],
                    perm=[1, 0],  # Swap dimensions
                    name=f"{node.name}_transpose"
                )
                new_nodes.append(transpose_node)
                matmul_input_b = transpose_output

            # Create MatMul node
            matmul_output = f"{output}_matmul"
            matmul_node = helper.make_node(
                'MatMul',
                inputs=[input_a, matmul_input_b],
                outputs=[matmul_output],
                name=f"{node.name}_matmul"
            )
            new_nodes.append(matmul_node)

            # Create Add node for bias
            if input_c:
                add_node = helper.make_node(
                    'Add',
                    inputs=[matmul_output, input_c],
                    outputs=[output],
                    name=f"{node.name}_add"
                )
                new_nodes.append(add_node)
            else:
                # No bias, just rename MatMul output
                matmul_node.output[0] = output

            nodes_to_remove.append(node)
        else:
            new_nodes.append(node)

    # Rebuild graph with new nodes
    del graph.node[:]
    graph.node.extend(new_nodes)

    # Validate and save
    try:
        onnx.checker.check_model(model)
        print("✓ Model validation passed")
    except Exception as e:
        print(f"⚠️  Model validation warning: {e}")
        print("   Continuing anyway...")

    onnx.save(model, output_path)
    print(f"✅ Converted model saved: {output_path}")
    print(f"   Gemm nodes converted to MatMul+Add")

    return output_path

if __name__ == '__main__':
    input_model = 'model/rugdetector_v1_nn.onnx'
    output_model = 'model/rugdetector_v1_nn_matmul.onnx'

    if len(sys.argv) > 1:
        input_model = sys.argv[1]
    if len(sys.argv) > 2:
        output_model = sys.argv[2]

    convert_gemm_to_matmul(input_model, output_model)
