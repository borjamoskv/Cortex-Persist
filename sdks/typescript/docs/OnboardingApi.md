# OnboardingApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**signupV1SignupPost**](OnboardingApi.md#signupv1signuppost) | **POST** /v1/signup | Signup |



## signupV1SignupPost

> SignupResponse signupV1SignupPost(signupRequest)

Signup

Create a free-tier account. Returns API key immediately.  No email verification required for MVP - key is active on creation.

### Example

```ts
import {
  Configuration,
  OnboardingApi,
} from '';
import type { SignupV1SignupPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new OnboardingApi();

  const body = {
    // SignupRequest
    signupRequest: ...,
  } satisfies SignupV1SignupPostRequest;

  try {
    const data = await api.signupV1SignupPost(body);
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
| **signupRequest** | [SignupRequest](SignupRequest.md) |  | |

### Return type

[**SignupResponse**](SignupResponse.md)

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

