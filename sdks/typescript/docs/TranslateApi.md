# TranslateApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**translateTextsV1TranslatePost**](TranslateApi.md#translatetextsv1translatepost) | **POST** /v1/translate | Translate Texts |



## translateTextsV1TranslatePost

> TranslateResponse translateTextsV1TranslatePost(translateRequest, authorization)

Translate Texts

OMNI-TRANSLATE: Sovereign Core translation endpoint.  Translates a dictionary of texts into multiple target languages simultaneously using Gemini 2.0 Flash for optimal speed and cost. Ensures that the output strictly matches the input schema.

### Example

```ts
import {
  Configuration,
  TranslateApi,
} from '';
import type { TranslateTextsV1TranslatePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TranslateApi();

  const body = {
    // TranslateRequest
    translateRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies TranslateTextsV1TranslatePostRequest;

  try {
    const data = await api.translateTextsV1TranslatePost(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **translateRequest** | [TranslateRequest](TranslateRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**TranslateResponse**](TranslateResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

