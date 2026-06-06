# \TranslateApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**translate_texts_v1_translate_post**](TranslateApi.md#translate_texts_v1_translate_post) | **POST** /v1/translate | Translate Texts



## translate_texts_v1_translate_post

> models::TranslateResponse translate_texts_v1_translate_post(translate_request, authorization)
Translate Texts

OMNI-TRANSLATE: Sovereign Core translation endpoint.  Translates a dictionary of texts into multiple target languages simultaneously using Gemini 2.0 Flash for optimal speed and cost. Ensures that the output strictly matches the input schema.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**translate_request** | [**TranslateRequest**](TranslateRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::TranslateResponse**](TranslateResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

