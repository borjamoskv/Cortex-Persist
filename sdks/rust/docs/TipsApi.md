# \TipsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_tips_by_category_tips_category_category_get**](TipsApi.md#get_tips_by_category_tips_category_category_get) | **GET** /tips/category/{category} | Get Tips By Category
[**get_tips_by_project_tips_project_project_get**](TipsApi.md#get_tips_by_project_tips_project_project_get) | **GET** /tips/project/{project} | Get Tips By Project
[**get_tips_tips_get**](TipsApi.md#get_tips_tips_get) | **GET** /tips | Get Tips
[**list_categories_tips_categories_get**](TipsApi.md#list_categories_tips_categories_get) | **GET** /tips/categories | List Categories



## get_tips_by_category_tips_category_category_get

> models::TipsListResponse get_tips_by_category_tips_category_category_get(category, lang, limit, authorization)
Get Tips By Category

Get tips filtered by category.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**category** | **String** |  | [required] |
**lang** | Option<**String**> | Language code (en, es, eu) |  |[default to en]
**limit** | Option<**i32**> |  |  |[default to 5]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::TipsListResponse**](TipsListResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## get_tips_by_project_tips_project_project_get

> models::TipsListResponse get_tips_by_project_tips_project_project_get(project, lang, limit, authorization)
Get Tips By Project

Get tips scoped to a specific project.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**project** | **String** |  | [required] |
**lang** | Option<**String**> | Language code (en, es, eu) |  |[default to en]
**limit** | Option<**i32**> |  |  |[default to 3]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::TipsListResponse**](TipsListResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## get_tips_tips_get

> models::TipsListResponse get_tips_tips_get(count, lang, authorization)
Get Tips

Get random contextual tips.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**count** | Option<**i32**> | Number of tips to return |  |[default to 1]
**lang** | Option<**String**> | Language code (en, es, eu) |  |[default to en]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::TipsListResponse**](TipsListResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## list_categories_tips_categories_get

> models::CategoriesResponse list_categories_tips_categories_get(lang, authorization)
List Categories

List all tip categories with counts.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**lang** | Option<**String**> | Language code (en, es, eu) |  |[default to en]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::CategoriesResponse**](CategoriesResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

