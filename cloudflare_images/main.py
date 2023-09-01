from typing import Self
from urllib.parse import urlencode

import httpx
from pydantic import Field
from start_cloudflare import CF


class CloudflareImagesAPI(CF):
    """
    Need to setup a Cloudflare Images account to use. See Cloudflare Images [docs](https://developers.cloudflare.com/images/cloudflare-images/).
    With required variables secured:

    Field in .env | Cloudflare API Credential | Where credential found
    :--|:--:|:--
    `CF_ACCT_ID` | Account ID |  `https://dash.cloudflare.com/<acct_id>/images/images`
    `CF_IMG_HASH` | Account Hash | `https://dash.cloudflare.com/<acct_id>/images/images`
    `CF_IMG_TOKEN` | API Secret | Generate / save via `https://dash.cloudflare.com/<acct_id>/profile/api-tokens`

    Add secrets to .env file and use as follows:

    Examples:
        ```py title="Example Usage" linenums="1"
        >>> cf = CloudflareImagesAPI() # will error out since missing key values
        Traceback (most recent call last):
        pydantic_core._pydantic_core.ValidationError: 3 validation errors for CloudflareImagesAPI
        CF_ACCT_ID
          Field required [type=missing, input_value={}, input_type=dict]
            For further information visit https://errors.pydantic.dev/2.3/v/missing
        CF_IMG_HASH
          Field required [type=missing, input_value={}, input_type=dict]
            For further information visit https://errors.pydantic.dev/2.3/v/missing
        CF_IMG_TOKEN
          Field required [type=missing, input_value={}, input_type=dict]
            For further information visit https://errors.pydantic.dev/2.3/v/missing
        >>> import os
        >>> os.environ['CF_ACCT_ID'] = "ABC"
        >>> cf = CloudflareImagesAPI() # will error out since still missing other values
        Traceback (most recent call last):
        pydantic_core._pydantic_core.ValidationError: 2 validation errors for CloudflareImagesAPI
        CF_IMG_HASH
          Field required [type=missing, input_value={'CF_ACCT_ID': 'ABC'}, input_type=dict]
            For further information visit https://errors.pydantic.dev/2.3/v/missing
        CF_IMG_TOKEN
          Field required [type=missing, input_value={'CF_ACCT_ID': 'ABC'}, input_type=dict]
            For further information visit https://errors.pydantic.dev/2.3/v/missing
        >>> # we'll add all the values needed
        >>> os.environ['CF_IMG_HASH'], os.environ['CF_IMG_TOKEN'] = "DEF", "XYZ"
        >>> cf = CloudflareImagesAPI() # no longer errors out
        >>> CF.set_bearer_auth(cf.api_token)
        {'Authorization': 'Bearer XYZ'}
        >>> cf.base_api
        'https://api.cloudflare.com/client/v4/accounts/ABC/images/v1'
        >>> cf.base_delivery
        'https://imagedelivery.net/DEF'
        >>> cf.url('hi-bob', 'w=400,sharpen=3')
        'https://imagedelivery.net/DEF/hi-bob/w=400,sharpen=3'
        >>> from pathlib import Path
        >>> p = Path().cwd() / "img" / "screenshot.png"
        >>> p.exists() # Sample image found in `/img/screenshot.png`
        True
        >>> import io
        >>> img = io.BytesIO(p.read_bytes())
        >>> type(img)
        <class '_io.BytesIO'>
        >>> # Can now use img in `cf.post('sample_id', img)`
        ```
    """  # noqa: E501

    account_id: str = Field(
        default=...,
        repr=False,
        title="Cloudflare Account ID",
        description="Overrides the base setting by making this mandatory.",
        validation_alias="CF_ACCT_ID",
    )
    cf_img_hash: str = Field(
        default=...,
        repr=False,
        title="Cloudflare Image Hash",
        description="Assigned when you create a Cloudflare Images account",
        validation_alias="CF_IMG_HASH",
    )
    api_token: str = Field(
        default=...,
        repr=False,
        title="Cloudflare Image API Token",
        description="Secure token to perform API operations",
        validation_alias="CF_IMG_TOKEN",
    )
    client_api_ver: str = Field(
        default="v4",
        title="Cloudflare Client API Version",
        description="Used in the middle of the URL in API requests.",
        validation_alias="CLOUDFLARE_CLIENT_API_VERSION",
    )
    images_api_ver: str = Field(
        default="v1",
        title="Cloudflare Images API Version",
        description="Used at the end of URL in API requests.",
        validation_alias="CLOUDFLARE_IMAGES_API_VERSION",
    )
    timeout: int = Field(
        default=60,
        validation_alias="CF_IMG_TOKEN_TIMEOUT",
    )
    is_batch: bool = Field(
        default=False, description="When True, will use a different endpoint."
    )

    @property
    def client(self):
        return httpx.Client(timeout=self.timeout)

    @property
    def base_api(self) -> str:
        """Construct endpoint. See [formula](https://developers.cloudflare.com/images/cloudflare-images/api-request/).

        Examples:
            >>> import os
            >>> os.environ['CF_ACCT_ID'] = "ABC"
            >>> os.environ['CF_IMG_HASH'], os.environ['CF_IMG_TOKEN'] = "DEF", "XYZ"
            >>> cf = CloudflareImagesAPI()
            >>> cf.base_api
            'https://api.cloudflare.com/client/v4/accounts/ABC/images/v1'
            >>> cf.is_batch = True
            >>> cf.base_api
            'https://batch.imagedelivery.net'

        Returns:
            str: URL endpoint to make requests with the Cloudflare-supplied credentials.
        """
        if self.is_batch:
            # See https://developers.cloudflare.com/images/cloudflare-images/upload-images/images-batch/
            return "https://batch.imagedelivery.net"
        return self.add_account_endpoint(
            f"/{self.account_id}/images/{self.images_api_ver}"
        )

    @property
    def v2(self) -> str:
        """See updated [list API endpoint](https://developers.cloudflare.com/api/operations/cloudflare-images-list-images-v2).

        Examples:
            >>> import os
            >>> os.environ['CF_ACCT_ID'] = "ABC"
            >>> os.environ['CF_IMG_HASH'], os.environ['CF_IMG_TOKEN'] = "DEF", "XYZ"
            >>> cf = CloudflareImagesAPI()
            >>> cf.v2
            'https://api.cloudflare.com/client/v4/accounts/ABC/images/v2'
        """
        return self.add_account_endpoint(f"/{self.account_id}/images/v2")

    @property
    def base_delivery(self):
        """Images are served with the following format: `https://imagedelivery.net/<ACCOUNT_HASH>/<IMAGE_ID>/<VARIANT_NAME>`

        This property constructs the first part: `https://imagedelivery.net/<ACCOUNT_HASH>`

        See Cloudflare [docs](https://developers.cloudflare.com/images/cloudflare-images/serve-images/).

        Examples:
        >>> import os
            >>> os.environ['CF_ACCT_ID'] = "ABC"
            >>> os.environ['CF_IMG_HASH'], os.environ['CF_IMG_TOKEN'] = "DEF", "XYZ"
            >>> cf = CloudflareImagesAPI()
            >>> cf.base_delivery
            'https://imagedelivery.net/DEF'
        """  # noqa: E501
        return "/".join(["https://imagedelivery.net", self.cf_img_hash])

    def url(self, img_id: str, variant: str = "public") -> str:
        """Generates url based on the Cloudflare hash of the account. The `variant` is based on
        how these are customized on Cloudflare Images. See also flexible variant [docs](https://developers.cloudflare.com/images/cloudflare-images/transform/flexible-variants/)

        Examples:
            >>> import os
            >>> os.environ['CF_ACCT_ID'] = "ABC"
            >>> os.environ['CF_IMG_HASH'], os.environ['CF_IMG_TOKEN'] = "DEF", "XYZ"
            >>> cf = CloudflareImagesAPI()
            >>> cf.url('sample-img', 'avatar')
            'https://imagedelivery.net/DEF/sample-img/avatar'

        Args:
            img_id (str): The uploaded ID
            variant (str, optional): The variant created in the Cloudflare Images dashboard. Defaults to "public".

        Returns:
            str: URL to display the request `img_id` with `variant`.
        """  # noqa: E501
        return "/".join([self.base_delivery, img_id, variant])

    def get_usage_statistics(self) -> httpx.Response:
        """Fetch usage statistics details for Cloudflare Images. See [API](https://developers.cloudflare.com/api/operations/cloudflare-images-images-usage-statistics)

        Returns:
            httpx.Response: Response containing the counts for `allowed` and `current in the result key
        """  # noqa: E501
        return self.client.get(
            url=f"{self.base_api}/stats",
            headers=CF.set_bearer_auth(self.api_token),
        )

    def get_batch_token(self) -> httpx.Response:
        """Get a token to use [Images batch API](https://developers.cloudflare.com/images/cloudflare-images/upload-images/images-batch/) for several requests in sequence bypassing Cloudflare's global API rate limits.
        Note that the token has a expiration time indicated in the response.

        Returns:
            httpx.Response: Response containing the batch `token` in the result key
        """  # noqa: E501
        return self.client.get(
            url=f"{self.base_api}/batch_token",
            headers=CF.set_bearer_auth(self.api_token),
        )

    def get_image_details(self, img_id: str, *args, **kwargs) -> httpx.Response:
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
            headers=CF.set_bearer_auth(self.api_token),
            *args,
            **kwargs,
        )

    def update_image(self, img_id: str, *args, **kwargs) -> httpx.Response:
        """Update image access control. On access control change, all copies of the image are purged from cache.

        Issue httpx [PATCH](https://developers.cloudflare.com/api/operations/cloudflare-images-update-image) request to the image.
        """  # noqa: E501
        return self.client.patch(
            url=f"{self.base_api}/{img_id}",
            headers=CF.set_bearer_auth(self.api_token),
            *args,
            **kwargs,
        )

    def delete_image(self, img_id: str, *args, **kwargs) -> httpx.Response:
        """Issue httpx [DELETE](https://developers.cloudflare.com/images/cloudflare-images/transform/delete-images/) request to the image."""  # noqa: E501
        return self.client.delete(
            url=f"{self.base_api}/{img_id}",
            headers=CF.set_bearer_auth(self.api_token),
            *args,
            **kwargs,
        )

    def upload_image(self, img_id: str, img: bytes, *args, **kwargs) -> httpx.Response:
        """Issue httpx [POST](https://developers.cloudflare.com/images/cloudflare-images/upload-images/upload-via-url/) request to upload image."""  # noqa: E501
        return self.client.post(
            url=self.base_api,
            headers=CF.set_bearer_auth(self.api_token),
            data={"id": img_id},
            files={"file": (img_id, img)},
            *args,
            **kwargs,
        )

    def delete_then_upload_image(self, img_id: str, img: bytes) -> httpx.Response:
        """Ensures a unique id name by first deleting the `img_id` from storage and then
        uploading the `img`."""
        self.delete_image(img_id)
        return self.upload_image(img_id, img)

    def list_images(
        self,
        per_page: int = 1000,
        sort_order: str = "desc",
        continuation_token: str | None = None,
    ) -> httpx.Response:
        """See [list images API](https://developers.cloudflare.com/api/operations/cloudflare-images-list-images-v2).

        Args:
            per_page (int, optional): Number of items per page (10 to 10,000). Defaults to 1000.
            sort_order (str, optional): Sorting order by upload time (asc | desc). Defaults to "desc".
            continuation_token (str | None, optional): Continuation token for a next page. List images V2 returns continuation_token. Defaults to None.

        Returns:
            httpx.Response: Contains top-level fields for `success`, `errors`, `messages` and the `result`.
        """  # noqa: E501

        if per_page < 10 or per_page > 10000:
            raise Exception(f"Improper {per_page=}")
        if sort_order not in ["asc", "desc"]:
            raise Exception(f"Improper {sort_order=}")
        params = {"per_page": per_page, "sort_order": sort_order}

        if continuation_token:
            params["continuation_token"] = continuation_token
        qs = urlencode(params)

        return self.client.get(
            url=f"{self.v2}?{qs}", headers=CF.set_bearer_auth(self.api_token)
        )

    def create_batch_api(self) -> Self:
        """Use the instance to generate a batch token then return a new
        API instance where the token is used, e.g.:

        ```py
        raw = CloudflareImagesAPI()
        api = cf.create_batch_api()
        ```

        Should now be able to use batch.upload_image(), batch.list_images() instead of
        the raw.upload_image(), etc. methods. See the [docs](https://developers.cloudflare.com/images/cloudflare-images/upload-images/images-batch/)
        """  # noqa: E501
        try:
            res = self.get_batch_token()
            data = res.json()
            token = data["result"]["token"]
        except Exception as e:
            raise Exception(f"Could not generate batch token; {e=}")
        return CloudflareImagesAPI(CF_IMG_TOKEN=token, is_batch=True)  # type: ignore # noqa: E501
