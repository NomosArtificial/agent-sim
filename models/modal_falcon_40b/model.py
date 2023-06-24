"""
Adapted from https://modal.com/docs/guide/ex/falcon_gptq
"""

from modal import Image, Stub, gpu, method, web_endpoint


IMAGE_MODEL_DIR = "/model"


def download_model():
    from huggingface_hub import snapshot_download

    model_name = "TheBloke/falcon-40b-instruct-GPTQ"
    snapshot_download(model_name, local_dir=IMAGE_MODEL_DIR)


image = (
    Image.debian_slim(python_version="3.10")
    .apt_install("git")
    .pip_install(
        "huggingface_hub==0.14.1",
        "transformers @ git+https://github.com/huggingface/transformers.git@f49a3453caa6fe606bb31c571423f72264152fce",
        "auto-gptq @ git+https://github.com/PanQiWei/AutoGPTQ.git@b5db750c00e5f3f195382068433a3408ec3e8f3c",
        "einops==0.6.1",
    )
    .run_function(download_model)
)

stub = Stub(image=image, name="falcon-40b-instruct")


@stub.cls(gpu=gpu.A100(), timeout=60 * 10, container_idle_timeout=60 * 5)
class Falcon40BGPTQ:
    def __enter__(self):
        from transformers import AutoTokenizer
        from auto_gptq import AutoGPTQForCausalLM

        self.tokenizer = AutoTokenizer.from_pretrained(IMAGE_MODEL_DIR, use_fast=True)
        print("Loaded tokenizer.")

        self.model = AutoGPTQForCausalLM.from_quantized(
            IMAGE_MODEL_DIR,
            trust_remote_code=True,
            use_safetensors=True,
            device_map="auto",
            use_triton=False,
            strict=False,
        )
        print("Loaded model.")

    @method()
    def generate(self, prompt: str, temperature: float, max_new_tokens: int):
        from threading import Thread
        from transformers import TextIteratorStreamer

        inputs = self.tokenizer(prompt, return_tensors="pt")
        streamer = TextIteratorStreamer(self.tokenizer, skip_special_tokens=True)
        generation_kwargs = dict(
            inputs=inputs.input_ids.cuda(),
            attention_mask=inputs.attention_mask,
            eos_token_id=self.tokenizer.eos_token_id,
            pad_token_id=self.tokenizer.eos_token_id,
            bos_token_id=self.tokenizer.bos_token_id,
            temperature=temperature,
            max_new_tokens=max_new_tokens,
            streamer=streamer,
        )

        # Run generation on separate thread to enable response streaming.
        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()
        for new_text in streamer:
            yield new_text

        thread.join()


@stub.function(timeout=60 * 10)
@web_endpoint(method="POST")
def get(body: dict):
    from fastapi.responses import JSONResponse

    model = Falcon40BGPTQ()
    buffer = ""

    for text in model.generate.call(
        body["prompt"], body["temperature"], body["max_new_tokens"]
    ):
        buffer += text

    return JSONResponse({"prompt": buffer})
