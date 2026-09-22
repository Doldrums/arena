Stable Diffusion excess blue

Source: Language Model Crossover, Section 4.4 and Appendix D
https://arxiv.org/abs/2302.12170
https://github.com/jal278/lmx/tree/b8fec5dd16451cf7afb6e02ac621b71d5bdfee7f

Protocol: arena.lmx-sd14-excess-rgb/1 (source-derived; paper reproduction not verified).

Candidate interface
candidate() -> str (at most 4096 UTF-8 bytes; SD tokenizer retains its native 77-token limit). The grader renders one full 512x512 RGB image with fixed SD1.4 fp16/10 steps/seed 99 and maximizes the selected channel sum minus half each other channel sum.

Evaluation
Source-derived GPU evaluation: full 512x512 SD1.4 fp16 image, 10 diffusion steps, fixed seed 99, enabled safety checker and original excess-channel score. Dimensions,steps,fp16 and safety filter follow paper Appendix D.

Arena initialization is the shared neutral prompt A photograph of a landscape. It replaces a non-executable placeholder and does not reproduce the paper's sampled human-prompt population or 5000-evaluation search protocol.

Guidance 7.5, negative_prompt=None, one image, PNDM scheduler from pinned checkpoint, legacy AttnProcessor, disabled TF32, deterministic cuDNN settings and modern pinned package versions are explicit Arena protocol choices. Published paper scores are not comparable by default.

Candidate Python runs in a separate child with 3 CPU seconds, 512 MiB address-space, 5-second wall and 32 KiB output bounds; only a bounded UTF-8 prompt string is accepted. Parent verifies readonly model files and initializes its pipeline after the child exits. A same-UID container is not an adversarial secrecy boundary.

Canonical score is raw excess color. The separate normalized_excess divides by 66846720 only for display. A safety-filtered black image remains a valid zero-score result, matching the source evaluator.

A pinned GPU runtime and complete model assets are required; production GPU admission and fresh canonical readiness remain separate from private seed probes.

Prepared assets
Use scripts/deployment/prepare_lmx_sd_assets.py with tasks/adapters/lmx_sd_assets.json.
Set LMX_SD_ASSETS_DIR to the readonly complete asset directory. The evaluator
verifies every model/config/tokenizer/license file before constructing the model.
The candidate runs in a bounded child; it never supplies an image or score.
The environment must expose exactly one approved CUDA device and pin the runtime.

Run
python evaluator.py initial_program.py

Licenses
Original objective code: tasks/licenses/LMX-LICENSE.
Model: tasks/licenses/Stable-Diffusion-LICENSE.txt (CreativeML OpenRAIL-M).
No unknown-license human prompt dataset is downloaded or redistributed.

Resource limit
The trusted grader caps the PyTorch CUDA allocator at 8 GiB. This is not a
hardware VRAM limit; driver/context allocations are measured separately.
