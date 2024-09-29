import os
from io import BytesIO

import modal
from helpers import TelegramBot, Database

image = modal.Image.debian_slim().pip_install(
    "Pillow",
    "diffusers",
    "transformers",
    "accelerate",
    "safetensors",
    "psycopg2-binary",
)

app = modal.App("image_generation_bot", image=image)


@app.cls(
    gpu=modal.gpu.Any(),
    container_idle_timeout=60,
    secrets=[modal.Secret.from_name("secret-keys")],
)
class Model:
    @modal.build()
    def download_models(self):
        import torch
        from diffusers import StableDiffusionPipeline

        StableDiffusionPipeline.from_pretrained(
            "CompVis/stable-diffusion-v1-4",
            torch_dtype=torch.float16,
            cache_dir="/models",
        )

        # Create the table if it doesn't exist already
        Database().create_table()

    @modal.enter()
    def enter(self):
        import torch
        from diffusers import StableDiffusionPipeline

        self.pipe = StableDiffusionPipeline.from_pretrained(
            "CompVis/stable-diffusion-v1-4",
            torch_dtype=torch.float16,
            cache_dir="/models",
            local_files_only=True,
        ).to("cuda")

    @modal.method()
    def inference(self, user_id: int, prompt: str):
        output_image = self.pipe(prompt).images[0]

        byte_stream = BytesIO()
        output_image.save(byte_stream, format="PNG")
        image_bytes = byte_stream.getvalue()

        TelegramBot().sendPhoto(user_id, image_bytes)
        Database().decrement_credits(user_id)


@app.function(
    gpu=False,
    secrets=[modal.Secret.from_name("secret-keys")],
    image=modal.Image.debian_slim().pip_install("requests", "psycopg2-binary"),
)
@modal.web_endpoint(method="POST", wait_for_response=False)
def web_inference(msg: dict):

    # Check for `client_reference_id`, if its present then its Stripe webhook
    try:
        client_reference_id = msg["data"]["object"]["client_reference_id"]
        # Adding 50 credits to the user's account
        Database().update_credits(client_reference_id, 50)
        TelegramBot().sendMessage(
            client_reference_id,
            f"Your account has been credited with 50 credits. You can now generate images.",
        )
        return
    except KeyError:
        pass

    user_id = msg["message"]["from"]["id"]
    prompt = msg["message"]["text"]
    first_name = msg["message"]["from"]["first_name"] or "there"
    if prompt == "/start":
        TelegramBot().sendMessage(
            user_id,
            f"Hi {first_name}, I am a bot that can generate images from text. Please enter a prompt.",
        )
        # Since the first message is always "/start", we create a new user in the database
        Database().create_user(user_id)
    else:
        user_credits = Database().get_credits(user_id)

        if user_credits <= 0:
            TelegramBot().sendMessage(
                user_id,
                f"Sorry {first_name}, you do not have enough credits to generate an image. Please buy more credits to continue. Purchase 50 credits for $10 here: {os.getenv('STRIPE_PAYMENT_LINK')}?client_reference_id={user_id}",
            )
        else:
            TelegramBot().sendMessage(
                user_id,
                f"Sure {first_name}, generating an image for the prompt: {prompt}",
            )
            TelegramBot().sendPhotoUploadAction(user_id)
            Model().inference.spawn(user_id, prompt)
