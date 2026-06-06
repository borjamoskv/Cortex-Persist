# \OnboardingApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**signup_v1_signup_post**](OnboardingApi.md#signup_v1_signup_post) | **POST** /v1/signup | Signup



## signup_v1_signup_post

> models::SignupResponse signup_v1_signup_post(signup_request)
Signup

Create a free-tier account. Returns API key immediately.  No email verification required for MVP - key is active on creation.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**signup_request** | [**SignupRequest**](SignupRequest.md) |  | [required] |

### Return type

[**models::SignupResponse**](SignupResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

