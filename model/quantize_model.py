#!/usr/bin/env python3
"""
Quantize RugDetector model for zkML compatibility
Converts float32 inputs to int32 with fixed-point scaling
"""

import onnx
from onnx import numpy_helper
import numpy as np

def quantize_model(input_path, output_path, scale_factor=1000):
    """
    Quantize ONNX model to use integer inputs

    Args:
        input_path: Path to float32 ONNX model
        output_path: Path to save quantized int32 model
        scale_factor: Multiply floats by this to get integers (default 1000)
    """
    print(f"🔧 Quantizing model: {input_path}")
    print(f"📊 Scale factor: {scale_factor}")

    # Load the model
    model = onnx.load(input_path)

    # Get input info
    input_name = model.graph.input[0].name
    input_shape = [dim.dim_value for dim in model.graph.input[0].type.tensor_type.shape.dim]

    print(f"✓ Model loaded: {input_name} with shape {input_shape}")

    # Change input type from float32 to int32
    model.graph.input[0].type.tensor_type.elem_type = onnx.TensorProto.INT32

    # Add a Cast node to convert int32 input to float32 for the rest of the model
    cast_node = onnx.helper.make_node(
        'Cast',
        inputs=[input_name],
        outputs=[f'{input_name}_float'],
        to=onnx.TensorProto.FLOAT,
        name='input_cast_to_float'
    )

    # Add a Div node to scale down the integer input
    scale_constant_name = 'scale_factor'
    scale_value = np.array([scale_factor], dtype=np.float32)
    scale_tensor = numpy_helper.from_array(scale_value, name=scale_constant_name)

    div_node = onnx.helper.make_node(
        'Div',
        inputs=[f'{input_name}_float', scale_constant_name],
        outputs=[f'{input_name}_scaled'],
        name='input_scale_down'
    )

    # Update the first node to use the scaled input instead of original input
    first_node = model.graph.node[0]
    for i, inp in enumerate(first_node.input):
        if inp == input_name:
            first_node.input[i] = f'{input_name}_scaled'

    # Insert cast and div nodes at the beginning
    model.graph.node.insert(0, div_node)
    model.graph.node.insert(0, cast_node)

    # Add scale factor as initializer
    model.graph.initializer.append(scale_tensor)

    # Validate and save
    try:
        onnx.checker.check_model(model)
        print("✓ Model validation passed")
    except Exception as e:
        print(f"⚠️  Model validation warning: {e}")
        print("   Continuing anyway...")

    onnx.save(model, output_path)
    print(f"✅ Quantized model saved: {output_path}")
    print(f"📝 Use scale factor {scale_factor} when preparing inputs")
    print(f"   Example: int_input = float_input * {scale_factor}")

    return scale_factor

if __name__ == '__main__':
    import sys

    input_model = 'model/rugdetector_v1.onnx'
    output_model = 'model/rugdetector_v1_quantized.onnx'
    scale = 1000  # Scale floats by 1000 (3 decimal places precision)

    if len(sys.argv) > 1:
        scale = int(sys.argv[1])

    quantize_model(input_model, output_model, scale)
