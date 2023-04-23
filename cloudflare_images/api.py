from typing import Final

import httpx
from pydantic import BaseSettings, Field

CF_API_URL: Final = "https://api.cloudflare.com"
CF_DELIVER: Final = "https://imagedelivery.net"


class CloudflareImagesAPIv1(BaseSettings):
    """
    Need to setup a Cloudflare Images account to use. See Cloudflare Images [docs](https://developers.cloudflare.com/images/cloudflare-images/) API v4.
    With required variables secured:

    Field in .env | Cloudflare API Credential | Where credential found
    :--|:--:|:--
    `CF_IMG_ACCT` | Account ID |  `https://dash.cloudflare.com/<acct_id>/images/images`
    `CF_IMG_HASH` | Account Hash | `https://dash.cloudflare.com/<acct_id>/images/images`
    `CF_IMG_TOKEN` | API Secret | Generate / save via `https://dash.cloudflare.com/<acct_id>/profile/api-tokens`

    Add secrets to .env file and use as follows:

    Examples:
    ```py title="Example Usage" linenums="1" hl_lines="5 18"
    >>> from pathlib import Path
    >>> import os
    >>> import io
    >>> cf = CloudflareImagesAPIv1() # will error out since missing key values
    Traceback (most recent call last):
    pydantic.error_wrappers.ValidationError: 3 validation errors for CloudflareImagesAPIv1
    acct_id
      field required (type=value_error.missing)
    cf_img_hash
      field required (type=value_error.missing)
    api_token
      field required (type=value_error.missing)
    >>> os.environ['CF_ACCT_ID'] = "ABC"
    >>> cf = CloudflareImagesAPIv1() # will error out since still missing other values
    Traceback (most recent call last):
    pydantic.error_wrappers.ValidationError: 2 validation errors for CloudflareImagesAPIv1
    cf_img_hash
      field required (type=value_error.missing)
    api_token
      field required (type=value_error.missing)
    >>> # we'll add all the values needed
    >>> os.environ['CF_IMG_HASH'], os.environ['CF_IMG_TOKEN'] = "DEF", "XYZ"
    >>> cf = CloudflareImagesAPIv1() # no longer errors out
    >>> cf.headers
    {'Authorization': 'Bearer XYZ'}
    >>> cf.base_api
    'https://api.cloudflare.com/client/v4/accounts/ABC/images/v1'
    >>> cf.base_delivery
    'https://imagedelivery.net/DEF'
    >>> cf.url('hi-bob', 'w=400,sharpen=3')
    'https://imagedelivery.net/DEF/hi-bob/w=400,sharpen=3'
    >>> p = Path().cwd() / "img" / "screenshot.png"
    >>> p.exists() # Sample image found in `/img/screenshot.png`
    True
    >>> img = io.BytesIO(p.read_bytes())
    >>> type(img)
    <class '_io.BytesIO'>
    >>> # Can now use img in `cf.post('sample_id', img)`
    ```
    """  # noqa: E501

    acct_id: str = Field(
        default=...,
        repr=False,
        title="Cloudflare Account ID",
        description="Used in other Cloudflare services like R2, etc.",
        env="CF_ACCT_ID",
    )
    cf_img_hash: str = Field(
        default=...,
        repr=False,
        title="Cloudflare Image Hash",
        description="Assigned when you create a Cloudflare Images account",
        env="CF_IMG_HASH",
    )
    api_token: str = Field(
        default=...,
        repr=False,
        title="Cloudflare Image API Token",
        description="Secure token to perform API operations",
        env="CF_IMG_TOKEN",
    )
    client_api_ver: str = Field(
        default="v4",
        title="Cloudflare Client API Version",
        description="Used in the middle of the URL in API requests.",
        env="CLOUDFLARE_CLIENT_API_VERSION",
    )
    images_api_ver: str = Field(
        default="v1",
        title="Cloudflare Images API Version",
        description="Used at the end of URL in API requests.",
        env="CLOUDFLARE_IMAGES_API_VERSION",
    )
    timeout: int = Field(
        default=60,
        env="CF_IMG_TOKEN_TIMEOUT",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_token}"}

    @property
    def client(self):
        return httpx.Client(timeout=self.timeout)

    @property
    def base_api(self):
        """Construct URL based on Cloudflare API [format](https://developers.cloudflare.com/images/cloudflare-images/api-request/)"""  # noqa: E501
        client = f"client/{self.client_api_ver}"
        account = f"accounts/{self.acct_id}"
        images = f"images/{self.images_api_ver}"
        return "/".join([CF_API_URL, client, account, images])

    @property
    def base_delivery(self):
        """The images are served with the following format:

        `https://imagedelivery.net/<ACCOUNT_HASH>/<IMAGE_ID>/<VARIANT_NAME>`

        This property constructs the first part:

        `https://imagedelivery.net/<ACCOUNT_HASH>`

        See Cloudflare [docs](https://developers.cloudflare.com/images/cloudflare-images/serve-images/).

        """  # noqa: E501
        return "/".join([CF_DELIVER, self.cf_img_hash])

    def url(self, img_id: str, variant: str = "public"):
        """Generates url based on the Cloudflare hash of the account. The `variant` is based on
        how these are customized on Cloudflare Images. See also flexible variant [docs](https://developers.cloudflare.com/images/cloudflare-images/transform/flexible-variants/)
        """  # noqa: E501
        return "/".join([self.base_delivery, img_id, variant])

    def get(self, img_id: str, *args, **kwargs) -> httpx.Response:
        """Issue httpx GET request to the image found in storage. Assuming request like
        `CFImage().get('target-img-id')`, returns a response with metadata:

        Examples:
            ```py title="Response object from Cloudflare Images"
            >>> # CFImage().get('target-img-id') commented out since hypothetical
            b'{
                "result": {
                    "id": "target-img-id",
                    "filename": "target-img-id",
                    "uploaded": "2023-02-20T09:09:41.755Z",
                    "requireSignedURLs": false,
                    "variants": [
                        "https://imagedelivery.net/<hash>/<target-img-id>/public",
                        "https://imagedelivery.net/<hash>/<target-img-id>/cover",
                        "https://imagedelivery.net/<hash>/<target-img-id>/avatar",
                        "https://imagedelivery.net/<hash>/<target-img-id>/uniform"
                    ]
                },
                "success": true,
                "errors": [],
                "messages": []
            }'
            ```
        """
        return self.client.get(
            url=f"{self.base_api}/{img_id}",
            headers=self.headers,
            *args,
            **kwargs,
        )

    def delete(self, img_id: str, *args, **kwargs) -> httpx.Response:
        """Issue httpx [DELETE](https://developers.cloudflare.com/images/cloudflare-images/transform/delete-images/) request to the image."""  # noqa: E501
        return self.client.delete(
            url=f"{self.base_api}/{img_id}",
            headers=self.headers,
            *args,
            **kwargs,
        )

    def post(self, img_id: str, img: bytes, *args, **kwargs) -> httpx.Response:
        """Issue httpx [POST](https://developers.cloudflare.com/images/cloudflare-images/upload-images/upload-via-url/) request to upload image."""  # noqa: E501
        return self.client.post(
            url=self.base_api,
            headers=self.headers,
            data={"id": img_id},
            files={"file": (img_id, img)},
            *args,
            **kwargs,
        )

    def upsert(self, img_id: str, img: bytes) -> httpx.Response:
        """Ensures a unique id name by first deleting the `img_id` from storage and then
        uploading the `img`."""
        self.delete(img_id)
        return self.post(img_id, img)
