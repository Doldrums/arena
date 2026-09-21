"""Error categories shared by Metal evaluator components."""


class MetalKernelSafetyError(Exception):
    """Metal kernel safety violation"""

    pass


class GPUCommandBufferError(Exception):
    """GPU command buffer execution error"""

    pass


class MetalMemoryViolationError(Exception):
    """Metal kernel memory access violation"""

    pass
