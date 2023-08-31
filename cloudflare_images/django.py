from http import HTTPStatus

import httpx
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

from .api import CloudflareImagesAPIv1


@deconstructible
class LimitedStorageCloudflareImages(Storage):
    """Custom Storage Class based on Django docs [instructions](https://docs.djangoproject.com/en/dev/howto/custom-file-storage/#django.core.files.storage._open)

    Starting with Django 4.2, add to `STORAGES` setting:

    ```python title="Django settings.py" linenums="1" hl_lines="9 10"
    ...
    STORAGES = {  # django 4.2 and above
        "default": {  # default
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {  # default
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
        "cloudflare_images": {  # add
            "BACKEND": "cloudflare_images.django.ImageStorageCloudflare",
        },
    }
    ```

    Can then define a [callable](https://docs.djangoproject.com/en/dev/topics/files/#using-a-callable) likeso:

    ```python title="For use in ImageField"
    from django.core.files.storage import storages


    def select_storage(is_remote_env: bool):
        return storages["cloudflare_images"] if is_remote_env else storages["default"]


    class MyModel(models.Model):
        my_img = models.ImageField(storage=select_storage)
    ```

    Can also refer to it via:

    ```python title="Invocation"
    from django.core.files.storage import storages
    cf = storages["cloudflare_images"]

    # assume previous upload done
    id = <image-id-uploaded>

    # get image url, defaults to 'public' variant
    cf.url(id)

    # specified 'avatar' variant, assuming it was created in the Cloudflare Images dashboard / API
    cf.url_variant(id, 'avatar')
    ```


    """  # noqa: E501

    def __init__(self):
        super().__init__()
        self.api = CloudflareImagesAPIv1()

    def __repr__(self):
        return "<LimitedToImagesStorageClassCloudflare>"

    def _open(self, name: str, mode="rb") -> File:
        return File(self.api.get(img_id=name), name=name)

    def _save(self, name: str, content: bytes) -> str:
        res = self.api.upsert(name, content)
        return self.api.url(img_id=res.json()["result"]["id"])

    def get_valid_name(self, name):
        return name

    def get_available_name(self, name, max_length=None):
        return self.generate_filename(name)

    def generate_filename(self, filename):
        return filename

    def delete(self, name) -> httpx.Response:
        return self.api.delete(name)

    def exists(self, name: str) -> bool:
        res = self.api.get(name)
        if res.status_code == HTTPStatus.NOT_FOUND:
            return False
        elif res.status_code == HTTPStatus.OK:
            return True
        raise Exception("Image name found but http status code is not OK.")

    def listdir(self, path):
        raise NotImplementedError(
            "subclasses of Storage must provide a listdir() method"
        )

    def size(self, name: str):
        return len(self.api.get(name).content)

    def url(self, name: str):
        return self.api.url(name)

    def url_variant(self, name: str, variant: str):
        return self.api.url(name, variant)

    def get_accessed_time(self, name):
        raise NotImplementedError(
            "subclasses of Storage must provide a get_accessed_time() method"
        )

    def get_created_time(self, name):
        raise NotImplementedError(
            "subclasses of Storage must provide a get_created_time() method"
        )

    def get_modified_time(self, name):
        raise NotImplementedError(
            "subclasses of Storage must provide a get_modified_time() method"
        )
